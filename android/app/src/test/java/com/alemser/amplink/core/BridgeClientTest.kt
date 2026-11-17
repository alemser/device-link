package com.alemser.amplink.core

import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** The client against a fake device: the routes of docs/contract-v2.md, as the SP103 and the CD-S300 answer them. */
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
    fun readsTheDescription() = runBlocking {
        answer(javaClass.classLoader!!.getResource("sp103-device.json")!!.readText())
        val d = client.description()
        assertEquals("SP103-D4FE", d.name)
        assertEquals("/device", server.takeRequest().path)
    }

    @Test
    fun aBadAnswerIsAnIoError() = runBlocking {
        answer("<html>")
        val failed = runCatching { client.description() }.exceptionOrNull()
        assertTrue(failed is BridgeError)
    }

    @Test
    fun settingsArePatchedOnlyWithWhatChanges() = runBlocking {
        answer("""{"inputs.TUNER": "Rega Planar 2", "vu.on": true}""")
        val all = client.patchSettings(buildJsonObject { put("vu.on", JsonPrimitive(true)) })
        assertEquals("Rega Planar 2", all["inputs.TUNER"]!!.jsonPrimitive.content)
        val sent = server.takeRequest()
        assertEquals("PATCH", sent.method)
        assertEquals("/settings", sent.path)
        assertEquals("""{"vu.on":true}""", sent.body.readUtf8())
    }

    @Test
    fun aRefusedSettingShowsTheDevicesMessage() = runBlocking {
        answer("""{"id": "info.secs", "error": "the seconds per screen must be a whole number from 3 to 60"}""", 400)
        val failed = runCatching { client.patchSettings(buildJsonObject { put("info.secs", JsonPrimitive(99)) }) }
        assertEquals("the seconds per screen must be a whole number from 3 to 60", failed.exceptionOrNull()?.message)
    }

    @Test
    fun controlsGoToTheDeviceAsPosts() = runBlocking {
        repeat(3) { answer("{}") }
        client.step("bass", up = true)
        client.switch("loudness", on = false)
        client.press("select_cd")
        val requests = List(3) { server.takeRequest() }
        assertEquals(listOf("POST", "POST", "POST"), requests.map { it.method })
        assertEquals(
            listOf("/control?target=bass&dir=up", "/control?target=loudness&on=0", "/control?target=key&name=select_cd"),
            requests.map { it.path },
        )
    }

    @Test
    fun theStreamSkipsCommentsAndBadEvents() = runBlocking {
        server.enqueue(
            MockResponse()
                .setHeader("Content-Type", "text/event-stream")
                .setBody("data: {\"volume_db\": -20.0}\n\n: ping\n\ndata: {broken\n\n"),
        )
        val feed = client.feed().take(2).toList()
        assertEquals(-20.0, (feed[0] as Feed.Live).state["volume_db"]!!.jsonPrimitive.content.toDouble(), 0.0)
        assertTrue(feed[1] is Feed.Lost)
    }
}

class TextTest {
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
}
