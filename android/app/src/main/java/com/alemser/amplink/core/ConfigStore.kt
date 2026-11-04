package com.alemser.amplink.core

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.encodeToJsonElement
import kotlinx.serialization.json.jsonObject
import java.io.IOException

sealed interface SaveState {
    data object Idle : SaveState
    data object Waiting : SaveState
    data object Saving : SaveState
    data object Saved : SaveState

    /** A field can't go to the bridge as it is, so nothing was sent. */
    data class Invalid(val why: String) : SaveState
    data class Failed(val why: String) : SaveState
}

/**
 * The bridge's configuration, shared by the screens that edit it. Every edit shows at once and
 * reaches the bridge after a quiet moment, because each `PUT /names` writes to its flash and
 * redraws the display.
 */
class ConfigStore(
    private val client: BridgeClient,
    private val scope: CoroutineScope,
    private val quietMs: Long = QUIET_MS,
) {
    var names by mutableStateOf<Names?>(null)
        private set
    var config by mutableStateOf<Config?>(null)
        private set
    var loadError by mutableStateOf<String?>(null)
        private set
    var save by mutableStateOf<SaveState>(SaveState.Idle)
        private set

    private var raw = JsonObject(emptyMap())
    private var pending: Job? = null

    /** Called when a screen opens. An edit on its way to the bridge wins over what's stored there. */
    suspend fun load() {
        if (pending?.isActive == true) return
        try {
            val reply = client.names()
            raw = reply.rawConfig
            names = reply.names
            config = reply.names.config
            loadError = null
        } catch (e: IOException) {
            loadError = e.message ?: "Couldn't reach the bridge"
        }
    }

    fun edit(change: (Config) -> Config) {
        config = change(config ?: return)
        retry()
    }

    /** Sends the current configuration after the quiet moment. */
    fun retry() {
        pending?.cancel()
        save = SaveState.Waiting
        pending = scope.launch {
            delay(quietMs)
            push()
        }
    }

    private suspend fun push() {
        val edited = config ?: return
        invalidReason(edited)?.let {
            save = SaveState.Invalid(it)
            return
        }
        save = SaveState.Saving
        try {
            val reply = client.putConfig(overlay(raw, Wire.encodeToJsonElement(edited).jsonObject))
            raw = reply.rawConfig
            names = reply.names
            save = SaveState.Saved
        } catch (e: IOException) {
            save = SaveState.Failed(e.message ?: "Couldn't reach the bridge")
        }
    }

    private companion object {
        /** The contract asks for at least 1 s after the last change. */
        const val QUIET_MS = 1_000L
    }
}

internal fun invalidReason(config: Config): String? = when {
    !isIpv4(config.vu.relay) -> "The VU source must be an IP address"
    config.info.source.isNotEmpty() && !isIpv4(config.info.source) ->
        "The info source must be an IP address, or empty"
    else -> null
}

/** `edited` over `base`, object by object: what this app doesn't model stays as the bridge sent it. */
internal fun overlay(base: JsonObject, edited: JsonObject): JsonObject =
    JsonObject(
        base + edited.mapValues { (key, value): Map.Entry<String, JsonElement> ->
            val old = base[key]
            if (old is JsonObject && value is JsonObject) overlay(old, value) else value
        },
    )
