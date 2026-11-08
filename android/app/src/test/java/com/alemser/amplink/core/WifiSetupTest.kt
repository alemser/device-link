package com.alemser.amplink.core

import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.runTest
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
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import kotlin.concurrent.thread

/** Answers copied from the SP103 firmware on the bench Pico, 2026-11-08. */
private const val STATUS = """{"state": "connected", "ip": "10.185.11.138", "detail": "", "ssid": "Galaxy S26 Ale",
 "setup": {"ssid": "AmpLink-SP103-D85E", "open": false}}"""
private const val NETWORKS = """[{"rssi": -42, "secure": true, "ssid": "Galaxy S26 Ale"},
 {"rssi": -52, "secure": false, "ssid": "nhow"}]"""

class WifiSetupTest {
    private lateinit var server: MockWebServer
    private lateinit var client: WifiSetupClient

    @Before
    fun start() {
        server = MockWebServer()
        server.start()
        client = WifiSetupClient("${server.hostName}:${server.port}")
    }

    @After
    fun stop() = server.shutdown()

    private fun json(body: String, code: Int = 200) =
        MockResponse().setResponseCode(code).setHeader("Content-Type", "application/json").setBody(body)

    @Test
    fun readsStatusAndNetworks() = runBlocking {
        server.enqueue(json(STATUS))
        server.enqueue(json(NETWORKS))
        val status = client.status()
        assertEquals("connected", status.state)
        assertEquals("10.185.11.138", status.ip)
        assertEquals(SetupNetwork(open = false, ssid = "AmpLink-SP103-D85E"), status.setup)
        assertEquals("SP103-D85E", bridgeName(status.setup.ssid))
        val networks = client.networks()
        assertEquals(listOf("Galaxy S26 Ale", "nhow"), networks.map { it.ssid })
        assertFalse(networks[1].secure)
        assertEquals("/wifi", server.takeRequest().path)
        assertEquals("/wifi/networks", server.takeRequest().path)
    }

    @Test
    fun joinSendsTheNetworkAsJson() = runBlocking {
        server.enqueue(json("""{"state": "connecting", "detail": "Casa", "ip": ""}""", 202))
        client.join("Casa", "12345678")
        val request = server.takeRequest()
        assertEquals("PUT", request.method)
        assertEquals("/wifi", request.path)
        val body = Wire.parseToJsonElement(request.body.readUtf8()).jsonObject
        assertEquals("Casa", body["ssid"]?.jsonPrimitive?.content)
        assertEquals("12345678", body["psk"]?.jsonPrimitive?.content)
    }

    @Test
    fun theBridgesErrorIsShownAsItIs() = runBlocking {
        server.enqueue(json("""{"error": "open the setup network first: POST /wifi/setup"}""", 403))
        val error = runCatching { client.join("Casa", "12345678") }.exceptionOrNull()
        assertEquals("open the setup network first: POST /wifi/setup", error?.message)
    }

    @Test
    fun awaitOutcomeWaitsThroughConnectingAndLostAnswers() = runTest {
        server.enqueue(json("""{"state": "connecting", "detail": "Casa"}"""))
        server.enqueue(MockResponse().setResponseCode(500))      // the radio changing channel
        server.enqueue(json("""{"state": "failed", "detail": "wrong password", "ip": "10.0.0.5"}"""))
        val outcome = client.awaitOutcome(everyMs = 1)
        assertEquals("failed", outcome.state)
        assertEquals("wrong password", outcome.detail)
        assertTrue(outcome.finished)
    }

    @Test
    fun awaitOutcomeGivesUp() = runTest {
        repeat(5) { server.enqueue(json("""{"state": "connecting"}""")) }
        val outcome = client.awaitOutcome(timeoutMs = 3, everyMs = 1)
        assertEquals("failed", outcome.state)
    }

    @Test
    fun parsesDiscoveryAnswers() {
        assertEquals(
            FoundBridge("SP103-D85E", "sp103", "10.185.11.138"),
            parseAnswer("""{"name": "SP103-D85E", "model": "sp103", "ip": "10.185.11.138"}"""),
        )
        assertNull(parseAnswer("""{"name": "x", "ip": ""}"""))
        assertNull(parseAnswer("AMPLINK?"))
    }

    /** A fake bridge on localhost answers the probe, as the Pico does; the probe goes out three times. */
    @Test
    fun discoverCollectsEachBridgeOnce() = runBlocking {
        val bridge = DatagramSocket(0, InetAddress.getLoopbackAddress())
        var probes = 0
        val answering = thread {
            val buffer = ByteArray(64)
            runCatching {
                bridge.soTimeout = 3_000
                repeat(3) {
                    val packet = DatagramPacket(buffer, buffer.size)
                    bridge.receive(packet)
                    assertEquals("AMPLINK?", String(packet.data, 0, packet.length))
                    probes++
                    val answer = """{"name": "SP103-D85E", "model": "sp103", "ip": "127.0.0.1"}""".toByteArray()
                    bridge.send(DatagramPacket(answer, answer.size, packet.socketAddress))
                }
            }
        }
        val found = discover(listenMs = 200, target = InetAddress.getLoopbackAddress(), port = bridge.localPort)
        answering.join()
        bridge.close()
        assertEquals(3, probes)
        assertEquals(listOf(FoundBridge("SP103-D85E", "sp103", "127.0.0.1")), found)
    }
}
