package com.alemser.amplink.core

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.SocketTimeoutException
import java.util.concurrent.TimeUnit

/**
 * Wi-Fi without a cable and without typing the IP (docs/contract-v1.md, "Wi-Fi and discovery").
 *
 * A bridge with no working Wi-Fi opens its own network, named [SETUP_PREFIX] + its name, with the fixed
 * [SETUP_KEY]. The app joins it and uses [WifiSetupClient] at [SETUP_HOST]. On the home network, [discover] finds
 * the bridges by a UDP broadcast.
 */
const val SETUP_PREFIX = "AmpLink-"
const val SETUP_KEY = "amplink-setup"
const val SETUP_HOST = "192.168.4.1"
const val DISCOVERY_PORT = 47800
/** DeviceLink bridges answer both; today's SP103 only the first (docs/contract-v2.md, Discovery). */
private val PROBES = listOf("DEVICELINK?".toByteArray(), "AMPLINK?".toByteArray())

@Serializable
data class WifiNetwork(val ssid: String, val rssi: Int = 0, val secure: Boolean = true)

@Serializable
data class SetupNetwork(val open: Boolean = false, val ssid: String = "")

/** `state` and `detail` are the last attempt; `ip` is the bridge's address on the home network right now. */
@Serializable
data class WifiStatus(
    val state: String,
    val detail: String = "",
    val ip: String = "",
    val ssid: String = "",
    val setup: SetupNetwork = SetupNetwork(),
) {
    val finished get() = state == "connected" || state == "failed"
}

/**
 * A bridge's answer to the discovery broadcast. [name] is unique and stable (the chip's id), [label] the name to
 * show, [kind] the type of device. A bridge that doesn't say its [api] speaks api 1.
 */
@Serializable
data class FoundBridge(
    val name: String,
    val model: String = "",
    val ip: String,
    val label: String = "",
    val kind: String = "",
    val api: Int = SUPPORTED_API,
) {
    val title get() = label.ifEmpty { name }
}

/** The `/wifi` routes. [http] is bound to the bridge's setup network while the phone is on it. */
class WifiSetupClient(private val host: String, http: OkHttpClient = OkHttpClient()) {
    private val http = http.newBuilder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .callTimeout(15, TimeUnit.SECONDS)
        .build()

    suspend fun status(): WifiStatus = decode(http.fetch(request("/wifi").build()))

    /** The networks the bridge sees, strongest first. Takes a second: the bridge scans on the spot. */
    suspend fun networks(): List<WifiNetwork> = decode(http.fetch(request("/wifi/networks").build()))

    /** Starts joining `ssid`; the outcome comes from [awaitOutcome]. An empty `psk` means an open network. */
    suspend fun join(ssid: String, psk: String) {
        val body = buildJsonObject {
            put("ssid", ssid)
            put("psk", psk)
        }.toString().toRequestBody(JSON)
        http.fetch(request("/wifi").put(body).build())
    }

    /** Opens the setup network for 10 minutes, on a bridge that's on the home network. */
    suspend fun openSetup(): WifiStatus =
        decode(http.fetch(request("/wifi/setup").post(ByteArray(0).toRequestBody()).build()))

    /**
     * Asks `/wifi` until the join ends. A few lost answers are expected: the bridge's radio moves to the home
     * network's channel while joining, and the setup network moves with it.
     */
    suspend fun awaitOutcome(timeoutMs: Long = OUTCOME_TIMEOUT_MS, everyMs: Long = 1_000): WifiStatus {
        var waited = 0L
        var last: WifiStatus? = null
        while (waited < timeoutMs) {
            delay(everyMs)
            waited += everyMs
            last = runCatching { status() }.getOrNull() ?: last
            if (last?.finished == true) return last
        }
        return WifiStatus("failed", "The bridge didn't say whether it joined")
    }

    private fun request(path: String) = Request.Builder().url("http://$host$path")

    private companion object {
        val JSON = "application/json".toMediaType()

        /** The bridge gives up a network after 15 s, and may go back to the previous one after that. */
        const val OUTCOME_TIMEOUT_MS = 40_000L
    }
}

/**
 * Asks who's a bridge on the local network. The probe goes [tries] times: the first one is sometimes lost
 * while the bridge's radio wakes up. [open] makes the socket, so Android can bind it to the Wi-Fi network.
 */
suspend fun discover(
    tries: Int = 3,
    listenMs: Int = 700,
    target: InetAddress = InetAddress.getByName("255.255.255.255"),
    port: Int = DISCOVERY_PORT,
    open: () -> DatagramSocket = { DatagramSocket() },
): List<FoundBridge> = withContext(Dispatchers.IO) {
    val found = linkedMapOf<String, FoundBridge>()
    open().use { socket ->
        socket.broadcast = true
        socket.soTimeout = listenMs
        val buffer = ByteArray(512)
        repeat(tries) {
            PROBES.forEach { socket.send(DatagramPacket(it, it.size, target, port)) }
            while (true) {
                val packet = DatagramPacket(buffer, buffer.size)
                try {
                    socket.receive(packet)
                } catch (_: SocketTimeoutException) {
                    break
                }
                // Keyed by name: a bridge answering both probes is one device.
                parseAnswer(String(packet.data, 0, packet.length))?.let { found[it.name] = it }
            }
        }
    }
    found.values.toList()
}

internal fun parseAnswer(text: String): FoundBridge? = try {
    Wire.decodeFromString<FoundBridge>(text).takeIf { isIpv4(it.ip) }
} catch (_: SerializationException) {
    null
} catch (_: IllegalArgumentException) {
    null
}

/** The bridge's name from its setup network: "AmpLink-SP103-D85E" → "SP103-D85E". */
fun bridgeName(setupSsid: String): String = setupSsid.removePrefix(SETUP_PREFIX)
