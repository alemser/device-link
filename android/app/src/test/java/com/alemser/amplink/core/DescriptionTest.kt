package com.alemser.amplink.core

import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DescriptionTest {
    /** What the CD-S300 bridge answered on 2026-11-16 (version 00cdd591), trimmed to one group per kind. */
    private val cd = """
        {"api": 2, "kind": "cd_player", "model": "Yamaha CD-S300", "name": "CDS300-D85E", "bridge_version": "00cdd591",
         "firmware": "alemser/cds300-mod", "features": ["control", "update", "wifi_setup"],
         "state": [{"values": ["playing", "paused", "stopped", "loading", "open"], "id": "transport", "type": "enum"},
                   {"label": "Track", "id": "media.track", "type": "int"},
                   {"label": "Time", "id": "media.elapsed_s", "type": "duration"},
                   {"label": "Display", "id": "lcd", "type": "lines"}],
         "controls": [{"group": "transport", "keys": ["previous", "play", "stop"]},
                      {"group": "modes", "keys": ["repeat", {"key": "repeat_a_b", "label": "A-B"}]}]}
    """

    @Test
    fun readsTheCdPlayersDescription() {
        val d = decode<Description>(cd)
        assertEquals(2, d.api)
        assertEquals("cd_player", d.kind)
        assertEquals("alemser/cds300-mod", d.firmware)
        assertTrue(d.has("update"))
        assertEquals(listOf("transport", "media.track", "media.elapsed_s", "lcd"), d.state.map { it.id })
        assertEquals(listOf("playing", "paused", "stopped", "loading", "open"), d.state[0].values)
        assertEquals(listOf(KeyRef("previous"), KeyRef("play"), KeyRef("stop")), d.controls[0].keys)
        // A key may carry its own label.
        assertEquals(KeyRef("repeat_a_b", "A-B"), d.controls[1].keys[1])
    }

    @Test
    fun readsTheLiveStateAsJson() {
        val state = parseFeed("""data: {"transport": "playing", "media": {"track": 3, "elapsed_s": 127}, "lcd": ["  3    2:07 "]}""")!!
        assertEquals("playing", state["transport"]!!.jsonPrimitive.content)
        assertEquals(3, state["media"]!!.jsonObject["track"]!!.jsonPrimitive.int)
        assertNull(parseFeed(": ping"))
        assertNull(parseFeed("data: not json"))
    }

    /** The SP103 bridge's whole description (sp103-mod firmware/device.py, 2026-11-17), saved as a resource. */
    @Test
    fun readsTheAmplifiersDescription() {
        val json = javaClass.classLoader!!.getResource("sp103-device.json")!!.readText()
        val d = decode<Description>(json)
        assertEquals("amplifier", d.kind)
        assertEquals("alemser/sp103-mod", d.firmware)
        assertEquals(listOf("power", "volume", "input", "tone", "modes"), d.controls.map { it.group })
        assertEquals(KeyRef("power_toggle"), d.controls[0].keys[0])
        assertEquals("volume_db", d.controls[1].steps[0].state)
        val input = d.controls[2].select!!
        assertEquals("input_id", input.state)
        assertEquals(SelectOption("tape_aux", "TAPE/AUX", "select_tape_aux"), input.options[2])
        assertEquals(listOf("loudness", "speakers"), d.controls[4].switches.map { it.target })
        assertEquals("dB", d.state.first { it.id == "balance.db" }.unit)
    }

    @Test
    fun hashesLikeTheBridge() {
        // sha256 of "print(1)\n", as ota.py's _sha and enviar.py's sha compute it.
        assertEquals("cc42155088fca5730758db72b2a5bca33112a941dfaa2d43098ec422ce4ea213", sha256("print(1)\n".toByteArray()))
    }
}
