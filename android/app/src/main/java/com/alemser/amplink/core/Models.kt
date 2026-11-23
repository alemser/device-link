package com.alemser.amplink.core

import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNamingStrategy

/** The JSON of the DeviceLink contract (docs/contract-v2.md). A missing or null field means "not known". */
@OptIn(ExperimentalSerializationApi::class)
val Wire: Json = Json {
    namingStrategy = JsonNamingStrategy.SnakeCase
    ignoreUnknownKeys = true
    coerceInputValues = true
    explicitNulls = false
    encodeDefaults = true
}

/** The DeviceLink contract (docs/contract-v2.md): the device describes itself and the app builds its screen. */
const val DEVICELINK_API = 2

/** `GET /device` in api 2: what the device is, its state fields and its remote. */
@Serializable
data class Description(
    val api: Int,
    val kind: String = "",
    val model: String = "",
    val name: String = "",
    val bridgeVersion: String? = null,
    val firmware: String? = null,
    val features: List<String> = emptyList(),
    val state: List<StateField> = emptyList(),
    val controls: List<ControlGroup> = emptyList(),
) {
    fun has(feature: String) = feature in features
}

/** A state field: [id] is its path in the state JSON ("media.track"). */
@Serializable
data class StateField(
    val id: String,
    val type: String,
    val label: String? = null,
    val values: List<String> = emptyList(),
    val unit: String? = null,
    /** For `lines`: the display's width in characters. */
    val columns: Int? = null,
    /** For `lines`: the display's background and text colours ("#RRGGBB"), and whether its text glows (a VFD). */
    val glass: String? = null,
    val ink: String? = null,
    val glow: Boolean = false,
)

/** "#RRGGBB" as 0xAARRGGBB, opaque; null for anything else, so a bad colour falls back to the app's own. */
fun argb(hex: String?): Long? {
    if (hex == null || hex.length != 7 || hex[0] != '#') return null
    return hex.substring(1).toLongOrNull(16)?.let { 0xFF000000L or it }
}

/** One row or pad of the remote. A group holds keys, steps, switches or a select. */
@Serializable
data class ControlGroup(
    val group: String,
    val keys: List<KeyRef> = emptyList(),
    val steps: List<Bound> = emptyList(),
    val switches: List<Bound> = emptyList(),
    val select: Select? = null,
)

/** A key, sent as `POST /control?target=key&name=<key>`. Written as a plain string or `{"key", "label"}`. */
@Serializable(with = KeyRefSerializer::class)
data class KeyRef(val key: String, val label: String? = null)

/** A step (`dir=up/down`) or switch (`on=1/0`) [target], and the state field that shows its value. */
@Serializable
data class Bound(val target: String, val state: String? = null, val label: String? = null)

@Serializable
data class Select(val state: String? = null, val options: List<SelectOption> = emptyList())

@Serializable
data class SelectOption(val id: String, val name: String, val key: String)

/** `GET /update`: the running firmware and each file's sha256. */
@Serializable
data class UpdateStatus(
    val version: String,
    val state: String = "ok",
    val why: String? = null,
    val previous: String? = null,
    val files: Map<String, String> = emptyMap(),
    val staged: List<String> = emptyList(),
    /** The version the last update applied, kept after a rollback: tells this update's outcome from an older one. */
    val tried: String? = null,
)
