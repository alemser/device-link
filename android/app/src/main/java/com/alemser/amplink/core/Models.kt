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

/** The contract version this app speaks. */
const val SUPPORTED_API = 1

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
