package com.alemser.amplink.core

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** Answers copied from the real SP103 bridge, 2026-11-04. */
private const val DEVICE = """{"inputs": [{"id": "phono", "name": "PHONO"}, {"id": "tape_aux", "name": "TAPE/AUX"}],
 "display": {"columns": 16, "rows": 2}, "model": "Acoustic Solutions SP103",
 "features": ["tone", "config"], "volume_db": {"max": 0, "min": -78.75, "step": 1.25}, "api": 1,
 "tone_db": {"max": 14, "min": -14, "step": 1}, "bridge_version": "13f9fb61"}"""

private const val STATE_UNKNOWN = """{"updated_at": null, "firmware": null, "lcd": ["", ""], "input_name": null,
 "version": 0, "loudness": null, "bass_db": null, "screen": null, "volume_db": null, "speakers": null,
 "input_id": null, "treble_db": null, "power": null, "balance": null, "input": null}"""

private const val STATE = """{"power": "on", "volume_db": -20.0, "input": "DAB", "input_id": "dab",
 "input_name": "AirPlay/BT", "bass_db": 2, "treble_db": 0, "balance": {"side": null, "db": 0},
 "loudness": false, "speakers": true, "screen": "normal", "firmware": "1.0",
 "lcd": ["Volume -20.00 dB", "DAB             "], "updated_at": 3747990, "version": 5}"""

private const val NAMES = """{"inputs": ["PHONO", "TUNER"], "proxy": {"reads": 1, "writes": 1, "busy_high": 0},
 "screens": {"on": true, "error": null, "mode": "temp", "showing": null},
 "info": {"title": null, "last_packet_ms": 578, "playing": false, "stream": null, "on": true, "artist": null,
          "packets": 29362, "side_end": false},
 "defaults": {"about": ["Amplifier SP103", "SW version 1.0"], "boot": ["ACOUSTIC", "SOLUTIONS"]},
 "vu": {"on": true, "auto": true, "frames": 139405, "layout": "deck", "music": false, "floor": -42, "top": -22,
        "last_frame_ms": 21, "showing": false, "error": null},
 "vu_glyphs": {"bars": [1, 2]},
 "config": {"vu": {"on": true, "relay": "192.168.178.99", "auto": true, "layout": "deck"},
            "info": {"alert": true, "eu_dst": true, "mode": "temp", "show": ["pos", "side"], "on": true,
                     "scroll": true, "utc_offset": 0, "secs": 8, "source": "", "clock": true,
                     "turntable": ["PHONO"], "fixed": "quality", "future_field": 7},
            "boot": ["ACOUSTIC", "SOLUTIONS"], "inputs": {"TUNER": "Rega Planar 2"},
            "about": ["Oceano Amp", "AS SP103"]}}"""

private const val BUS = """{"last_screen_s": 299, "log_span_s": 7586, "max_batch": 1152, "log_words": 8192,
 "reads": 11968, "clock": "2026-11-04 14:21:35.236", "lcd": ["Volume -38.75 dB", "DAB             "],
 "power_ons": 0, "words": 23936, "max_gap_ms": 10033, "screens": 172, "since_s": 146828, "writes": 11968,
 "unknown_screens": 0, "maybe_lost": false, "log_size": 8192}"""

@OptIn(ExperimentalCoroutinesApi::class)
class BridgeClientTest {
    private lateinit var server: MockWebServer
    private lateinit var client: BridgeClient

    @Before
    fun start() {
        server = MockWebServer()
        server.start()
        client = BridgeClient("${server.hostName}:${server.port}")
    }

    @After
    fun stop() = server.shutdown()

    private fun answer(body: String, code: Int = 200) = server.enqueue(MockResponse().setResponseCode(code).setBody(body))

    @Test
    fun readsTheDevice() = runBlocking {
        answer(DEVICE)
        val device = client.device()
        assertEquals(1, device.api)
        assertEquals("13f9fb61", device.bridgeVersion)
        assertEquals(-78.75, device.volumeDb?.min)
        assertEquals("tape_aux", device.inputs[1].id)
        assertTrue(device.has("config"))
        assertFalse(device.has("vu"))
    }

    @Test
    fun readsBusStats() = runBlocking {
        answer(BUS)
        val stats = client.bus()
        assertEquals(10033L, stats.maxGapMs)
        assertEquals(146828L, stats.sinceS)
    }

    @Test
    fun aBadAnswerIsAnIoError() = runBlocking {
        answer("<html>")
        val failed = runCatching { client.device() }.exceptionOrNull()
        assertTrue(failed is BridgeError)
    }

    @Test
    fun aRefusedPutShowsTheBridgesMessage() = runBlocking {
        answer("""{"error": "the VU layout must be one of: bars"}""", 400)
        val failed = runCatching { client.putConfig(JsonObject(emptyMap())) }.exceptionOrNull()
        assertEquals("the VU layout must be one of: bars", failed?.message)
    }

    @Test
    fun theStreamSkipsCommentsAndBadEvents() = runBlocking {
        server.enqueue(
            MockResponse()
                .setHeader("Content-Type", "text/event-stream")
                .setBody("data: ${STATE.replace("\n", " ")}\n\n: ping\n\ndata: {broken\n\n"),
        )
        val links = client.live().take(2).toList()
        assertEquals(-20.0, (links[0] as Link.Live).state.volumeDb)
        assertTrue(links[1] is Link.Lost)
    }

    @Test
    fun anEditKeepsWhatTheAppDoesntKnowAndSendsEverything() = runTest {
        answer(NAMES)
        answer(NAMES)
        val store = ConfigStore(client, backgroundScope, quietMs = 1_000)
        runBlockingLoad(store)
        store.edit { it.copy(vu = it.vu.copy(layout = "bars")) }
        store.edit { it.copy(inputs = it.inputs + ("TUNER" to "")) }
        assertEquals(SaveState.Waiting, store.save)
        advanceTimeBy(999)
        runCurrent()
        assertEquals("only the GET so far", 1, server.requestCount)
        advanceTimeBy(2)
        runCurrent()
        waitFor { server.requestCount == 2 }

        server.takeRequest()
        val put = server.takeRequest()
        assertEquals("PUT", put.method)
        val sent = Wire.parseToJsonElement(put.body.readUtf8()).jsonObject
        assertEquals("bars", sent["vu"]!!.jsonObject["layout"]!!.jsonPrimitive.content)
        assertEquals("", sent["inputs"]!!.jsonObject["TUNER"]!!.jsonPrimitive.content)
        assertEquals(7, sent["info"]!!.jsonObject["future_field"]!!.jsonPrimitive.int)
        assertEquals(8, sent["info"]!!.jsonObject["secs"]!!.jsonPrimitive.int)
    }

    @Test
    fun anInvalidIpIsNotSent() = runTest {
        answer(NAMES)
        val store = ConfigStore(client, backgroundScope, quietMs = 1)
        runBlockingLoad(store)
        store.edit { it.copy(vu = it.vu.copy(relay = "192.168.")) }
        advanceTimeBy(5)
        runCurrent()
        assertTrue(store.save is SaveState.Invalid)
        assertEquals(1, server.requestCount)
    }

    private fun runBlockingLoad(store: ConfigStore) = runBlocking { store.load() }

    private fun waitFor(done: () -> Boolean) {
        val until = System.currentTimeMillis() + 3_000
        while (!done() && System.currentTimeMillis() < until) Thread.sleep(10)
        assertTrue(done())
    }
}

class ParsingTest {
    @Test
    fun anUnknownStateIsAllNull() {
        val state = parseEvent("data: " + STATE_UNKNOWN.replace("\n", " "))!!
        assertNull(state.power)
        assertNull(state.volumeDb)
        assertNull(state.balance)
    }

    @Test
    fun commentsAreNotEvents() {
        assertNull(parseEvent(": ping"))
        assertNull(parseEvent(""))
        assertNull(parseEvent("data: {broken"))
    }

    @Test
    fun overlayGoesObjectByObject() {
        val base = buildJsonObject {
            put("a", buildJsonObject { put("keep", JsonPrimitive(1)); put("change", JsonPrimitive(1)) })
        }
        val edited = buildJsonObject { put("a", buildJsonObject { put("change", JsonPrimitive(2)) }) }
        val a = overlay(base, edited)["a"]!!.jsonObject
        assertEquals(1, a["keep"]!!.jsonPrimitive.int)
        assertEquals(2, a["change"]!!.jsonPrimitive.int)
    }

    @Test
    fun lcdTextKeepsOnlyWhatTheDisplayHas() {
        assertEquals("Joao", lcdText("Joã\\o", 16))
        assertEquals("1234567890123456", lcdText("12345678901234567", 16))
        assertEquals("a", lcdText("a~", 16))
    }

    @Test
    fun ipv4() {
        assertTrue(isIpv4("192.168.178.108"))
        assertFalse(isIpv4("192.168."))
        assertFalse(isIpv4("192.168.178.256"))
        assertFalse(isIpv4(""))
    }

    @Test
    fun formats() {
        assertEquals("-20.00 dB", decibels(-20.0))
        assertEquals("+2 dB", decibels(2.0, signed = true))
        assertEquals("—", decibels(null))
        assertEquals("Centre", balanceText(Balance(null, 0.0)))
        assertEquals("L -5.00", balanceText(Balance("L", -5.0)))
        assertEquals("     ACOUSTIC   ".length, centred("ACOUSTIC", 16).length)
        assertEquals("    ACOUSTIC    ", centred("ACOUSTIC", 16))
        assertEquals("2 h 05 min", duration(7500))
    }
}
