package com.alemser.amplink.core

import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNamingStrategy

/** The JSON of the bridge contract (docs/contrato.md). A missing or null field means "not known". */
@OptIn(ExperimentalSerializationApi::class)
val Wire: Json = Json {
    namingStrategy = JsonNamingStrategy.SnakeCase
    ignoreUnknownKeys = true
    coerceInputValues = true
    explicitNulls = false
    encodeDefaults = true
}

/** The contract version of today's amplifier bridges (docs/contrato.md): shown with the amplifier tabs. */
const val SUPPORTED_API = 1

/** The DeviceLink contract (docs/contract-v2.md): the device describes itself and the app builds its screen. */
const val DEVICELINK_API = 2

/** `GET /device` in api 2: what the device is, its state fields, its remote and its settings. */
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
    val settings: List<SettingField> = emptyList(),
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
)

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

/** A value a person may change (`GET`/`PATCH /settings`). */
@Serializable
data class SettingField(
    val id: String,
    val type: String,
    val label: String? = null,
    val group: String? = null,
    val max: Double? = null,
    val min: Double? = null,
    val step: Double? = null,
    val charset: String? = null,
    val values: List<String> = emptyList(),
)

/** `GET /update`: the running firmware and each file's sha256. */
@Serializable
data class UpdateStatus(
    val version: String,
    val state: String = "ok",
    val why: String? = null,
    val previous: String? = null,
    val files: Map<String, String> = emptyMap(),
    val staged: List<String> = emptyList(),
)

@Serializable
data class Device(
    val api: Int,
    val model: String,
    val bridgeVersion: String? = null,
    val volumeDb: Scale? = null,
    val toneDb: Scale? = null,
    val inputs: List<DeviceInput> = emptyList(),
    val display: DisplaySize? = null,
    val features: List<String> = emptyList(),
) {
    fun has(feature: String) = feature in features
}

@Serializable
data class Scale(val min: Double, val max: Double, val step: Double)

@Serializable
data class DeviceInput(val id: String, val name: String)

@Serializable
data class DisplaySize(val columns: Int, val rows: Int)

@Serializable
data class AmpState(
    val power: String? = null,
    val volumeDb: Double? = null,
    val input: String? = null,
    val inputId: String? = null,
    val inputName: String? = null,
    val bassDb: Double? = null,
    val trebleDb: Double? = null,
    val balance: Balance? = null,
    val loudness: Boolean? = null,
    val speakers: Boolean? = null,
    val screen: String? = null,
    val firmware: String? = null,
    val lcd: List<String> = emptyList(),
    val version: Long = 0,
)

@Serializable
data class Balance(val side: String? = null, val db: Double = 0.0)

@Serializable
data class VuConfig(
    val on: Boolean = false,
    val auto: Boolean = true,
    val layout: String = "bars",
    val relay: String = "",
)

@Serializable
data class InfoConfig(
    val on: Boolean = false,
    val mode: String = "temp",
    val show: List<String> = emptyList(),
    val secs: Int = 8,
    val clock: Boolean = true,
    val utcOffset: Double = 0.0,
    val euDst: Boolean = true,
    val source: String = "",
    val turntable: List<String> = emptyList(),
)

/** What `PUT /names` takes. An input with an empty name goes back to the amp's own name. */
@Serializable
data class Config(
    val inputs: Map<String, String> = emptyMap(),
    val boot: List<String> = listOf("", ""),
    val about: List<String> = listOf("", ""),
    val vu: VuConfig = VuConfig(),
    val info: InfoConfig = InfoConfig(),
)

@Serializable
data class Defaults(val boot: List<String> = listOf("", ""), val about: List<String> = listOf("", ""))

@Serializable
data class VuStatus(
    val on: Boolean = false,
    val floor: Int? = null,
    val top: Int? = null,
    val lastFrameMs: Long? = null,
    val music: Boolean = false,
    val showing: Boolean = false,
    val error: String? = null,
)

@Serializable
data class InfoStatus(
    val lastPacketMs: Long? = null,
    val playing: Boolean = false,
    val stream: String? = null,
)

@Serializable
data class ScreensStatus(
    val on: Boolean = false,
    val showing: String? = null,
    val error: String? = null,
)

/** The answer of `GET` and `PUT /names`. */
@Serializable
data class Names(
    val config: Config = Config(),
    val inputs: List<String> = emptyList(),
    val defaults: Defaults = Defaults(),
    val vu: VuStatus? = null,
    val info: InfoStatus? = null,
    val screens: ScreensStatus? = null,
)

@Serializable
data class BusStats(
    val sinceS: Long? = null,
    val words: Long = 0,
    val writes: Long = 0,
    val reads: Long = 0,
    val powerOns: Long = 0,
    val screens: Long = 0,
    val unknownScreens: Long = 0,
    val lastScreenS: Long? = null,
    val maxGapMs: Long = 0,
    val maxBatch: Long = 0,
    val maybeLost: Boolean = false,
    val logWords: Long = 0,
    val logSize: Long = 0,
    val logSpanS: Long = 0,
    val clock: String? = null,
)
