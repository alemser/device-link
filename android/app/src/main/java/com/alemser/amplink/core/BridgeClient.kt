package com.alemser.amplink.core

import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.mapNotNull
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.math.min

/** The bridge answered with an error, or with something this app can't read. */
class BridgeError(message: String) : IOException(message)

/** Where the live stream stands. `Live` always holds a current reading: a stale one is never kept. */
sealed interface Link {
    data object Connecting : Link
    data class Live(val state: AmpState) : Link
    data class Lost(val why: String) : Link
}

/** An api 2 device's live state, as JSON: the description's state fields point into it (docs/contract-v2.md). */
sealed interface Feed {
    data object Connecting : Feed
    data class Live(val state: JsonObject) : Feed
    data class Lost(val why: String) : Feed
}

/** `Names` and the `config` exactly as it came, so a save keeps what this app doesn't know. */
data class NamesReply(val names: Names, val rawConfig: JsonObject)

/** The rules in "Para o cliente" of docs/contrato.md live here and in the screens that call this. */
class BridgeClient(val host: String) {
    private val http = OkHttpClient.Builder()
        .connectTimeout(CONNECT_TIMEOUT_S, TimeUnit.SECONDS)
        .callTimeout(CALL_TIMEOUT_S, TimeUnit.SECONDS)
        .build()

    /** Silence for this long means the stream died: the bridge pings every second. */
    private val streaming = http.newBuilder()
        .callTimeout(0, TimeUnit.SECONDS)
        .readTimeout(IDLE_TIMEOUT_S, TimeUnit.SECONDS)
        .build()

    suspend fun device(): Device = decode(send(request("/device")))

    /** api 2: the device's description, read once when its screen opens. */
    suspend fun description(): Description = decode(send(request("/device")))

    /** api 2: one key of the device's remote, by name. */
    suspend fun press(key: String) {
        post("/control?target=key&name=${java.net.URLEncoder.encode(key, "UTF-8")}")
    }

    /** api 2: the values a person may change. */
    suspend fun settings(): JsonObject = Wire.parseToJsonElement(send(request("/settings"))).jsonObject

    /** api 2: changes only the given settings; answers all of them. */
    suspend fun patchSettings(changes: JsonObject): JsonObject {
        val body = changes.toString().toRequestBody(JSON)
        return Wire.parseToJsonElement(send(request("/settings").newBuilder().patch(body).build())).jsonObject
    }

    /** The running firmware (`GET /update`). */
    suspend fun updateStatus(): UpdateStatus = decode(send(request("/update")))

    /** Stages one firmware file; the bridge answers its sha256. */
    suspend fun stage(name: String, data: ByteArray): String {
        val body = data.toRequestBody(OCTETS)
        val reply = send(request("/update/$name").newBuilder().put(body).build())
        return Wire.parseToJsonElement(reply).jsonObject["sha256"]?.jsonPrimitive?.content
            ?: throw BridgeError("The bridge didn't confirm $name")
    }

    /** Marks a firmware file for deletion at the next apply. */
    suspend fun stageDelete(name: String) {
        send(request("/update/$name").newBuilder().delete().build())
    }

    /** `cancel`, `apply` or `rollback`. The bridge restarts after apply and rollback. */
    suspend fun updateAction(action: String) {
        post("/update/$action")
    }

    /** api 2: the device's state, live, as JSON. Same rules as [live]: collect it from the device's open screen only. */
    fun feed(): Flow<Feed> = flow {
        var wait = RETRY_MIN_MS
        while (true) {
            try {
                rawEvents().collect { line ->
                    parseFeed(line)?.let {
                        wait = RETRY_MIN_MS
                        emit(Feed.Live(it))
                    }
                }
                emit(Feed.Lost("The device closed the connection"))
            } catch (e: IOException) {
                emit(Feed.Lost(e.message ?: "Connection lost"))
            }
            delay(wait)
            wait = min(wait * 2, RETRY_MAX_MS)
        }
    }

    suspend fun names(): NamesReply = namesReply(send(request("/names")))

    /** `config` must be complete: `PUT /names` replaces everything, and what's missing goes back to default. */
    suspend fun putConfig(config: JsonObject): NamesReply {
        val body = config.toString().toRequestBody(JSON)
        return namesReply(send(request("/names").newBuilder().put(body).build()))
    }

    suspend fun bus(): BusStats = decode(send(request("/bus.json")))

    suspend fun clearBus() {
        send(request("/bus/clear").newBuilder().post(ByteArray(0).toRequestBody()).build())
    }

    /** One step of `volume`, `bass`, `treble` or `balance`. The bridge does the clicks and waits for the amp. */
    suspend fun step(target: String, up: Boolean) {
        post("/control?target=$target&dir=${if (up) "up" else "down"}")
    }

    /** `loudness` or `speakers`. */
    suspend fun switch(target: String, on: Boolean) {
        post("/control?target=$target&on=${if (on) 1 else 0}")
    }

    /** One key of the remote, such as `power_toggle` or `select_cd`. */
    suspend fun key(command: String) {
        post("/ir/send?cmd=$command")
    }

    private suspend fun post(path: String) {
        send(request(path).newBuilder().post(ByteArray(0).toRequestBody()).build())
    }

    /**
     * The amp's state, live. The connection stays open only while this is collected, so collect
     * it from one screen, and only while that screen is on show.
     */
    fun live(): Flow<Link> = flow {
        var wait = RETRY_MIN_MS
        while (true) {
            try {
                events().collect {
                    wait = RETRY_MIN_MS
                    emit(Link.Live(it))
                }
                emit(Link.Lost("The bridge closed the connection"))
            } catch (e: IOException) {
                emit(Link.Lost(e.message ?: "Connection lost"))
            }
            delay(wait)
            wait = min(wait * 2, RETRY_MAX_MS)
        }
    }

    private fun events(): Flow<AmpState> = rawEvents().mapNotNull(::parseEvent)

    /** The lines of `/events`, as they come. */
    private fun rawEvents(): Flow<String> = callbackFlow {
        val call = streaming.newCall(request("/events"))
        call.enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                close(e)
            }

            override fun onResponse(call: Call, response: Response) {
                try {
                    response.use {
                        if (!it.isSuccessful) throw BridgeError("The bridge answered ${it.code}")
                        val source = it.body?.source() ?: throw BridgeError("Empty answer")
                        while (true) {
                            val line = source.readUtf8Line() ?: break
                            trySend(line)
                        }
                    }
                    close()
                } catch (e: IOException) {
                    close(e)
                }
            }
        })
        awaitClose { call.cancel() }
    }

    private fun request(path: String) = Request.Builder().url("http://$host$path").build()

    private suspend fun send(request: Request): String = http.fetch(request)

    private fun namesReply(body: String): NamesReply = try {
        val rawConfig = Wire.parseToJsonElement(body).jsonObject["config"]?.jsonObject
            ?: throw BridgeError("The bridge's answer has no configuration")
        NamesReply(Wire.decodeFromString(body), rawConfig)
    } catch (e: SerializationException) {
        throw BridgeError("Couldn't read the bridge's answer: ${e.message}")
    } catch (e: IllegalArgumentException) {
        throw BridgeError("Couldn't read the bridge's answer: ${e.message}")
    }

    private companion object {
        val JSON = "application/json".toMediaType()
        val OCTETS = "application/octet-stream".toMediaType()
        const val CONNECT_TIMEOUT_S = 5L

        /** Chosen: past the bridge's 10 s freeze (lwIP), so a slow answer isn't reported as a failure. */
        const val CALL_TIMEOUT_S = 15L
        const val IDLE_TIMEOUT_S = 5L
        const val RETRY_MIN_MS = 1_000L
        const val RETRY_MAX_MS = 30_000L
    }
}

/** One request, answered or failed: a bridge error comes back as [BridgeError] with the bridge's own message. */
internal suspend fun OkHttpClient.fetch(request: Request): String = suspendCancellableCoroutine { waiting ->
    val call = newCall(request)
    waiting.invokeOnCancellation { call.cancel() }
    call.enqueue(object : Callback {
        override fun onFailure(call: Call, e: IOException) {
            if (waiting.isActive) waiting.resumeWithException(e)
        }

        override fun onResponse(call: Call, response: Response) {
            val outcome = runCatching {
                response.use {
                    val body = it.body?.string().orEmpty()
                    if (!it.isSuccessful) throw BridgeError(errorMessage(body, it.code))
                    body
                }
            }
            if (waiting.isActive) outcome.fold(waiting::resume, waiting::resumeWithException)
        }
    })
}

internal inline fun <reified T> decode(body: String): T = try {
    Wire.decodeFromString<T>(body)
} catch (e: SerializationException) {
    throw BridgeError("Couldn't read the bridge's answer: ${e.message}")
} catch (e: IllegalArgumentException) {
    throw BridgeError("Couldn't read the bridge's answer: ${e.message}")
}

/** One line of the stream: the state in a `data:` line. Comments and bad events give null. */
internal fun parseEvent(line: String): AmpState? {
    if (!line.startsWith("data:")) return null
    return try {
        Wire.decodeFromString<AmpState>(line.removePrefix("data:").trim())
    } catch (_: SerializationException) {
        null
    } catch (_: IllegalArgumentException) {
        null
    }
}

/** One line of the stream as JSON (api 2), or null for comments and bad events. */
internal fun parseFeed(line: String): JsonObject? {
    if (!line.startsWith("data:")) return null
    return try {
        Wire.parseToJsonElement(line.removePrefix("data:").trim()) as? JsonObject
    } catch (_: SerializationException) {
        null
    } catch (_: IllegalArgumentException) {
        null
    }
}

/** The bridge's `{"error": "..."}`, which is written to be shown as it is. */
internal fun errorMessage(body: String, code: Int): String = try {
    Wire.parseToJsonElement(body).jsonObject["error"]?.jsonPrimitive?.content
} catch (_: SerializationException) {
    null
} catch (_: IllegalArgumentException) {
    null
} ?: "The bridge answered $code"
