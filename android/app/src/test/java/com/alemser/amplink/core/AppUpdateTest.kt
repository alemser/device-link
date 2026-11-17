package com.alemser.amplink.core

import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import java.nio.file.Files

class AppUpdateTest {
    private lateinit var server: MockWebServer
    private lateinit var updates: AppUpdate

    @Before
    fun start() {
        server = MockWebServer()
        server.start()
        updates = AppUpdate(api = server.url("").toString().trimEnd('/'))
    }

    @After
    fun stop() = server.shutdown()

    @Test
    fun picksTheNewestAppReleaseWithAnApk() = runBlocking {
        val apk = server.url("/devicelink-31.apk").toString()
        server.enqueue(
            MockResponse().setBody(
                """[{"tag_name": "app-29", "assets": [{"name": "devicelink-29.apk", "browser_download_url": "x"}]},
                    {"tag_name": "app-31", "body": "Faster", "assets": [{"name": "devicelink-31.apk", "browser_download_url": "$apk"}]},
                    {"tag_name": "app-40", "draft": true, "assets": [{"name": "devicelink-40.apk", "browser_download_url": "x"}]},
                    {"tag_name": "app-35", "assets": []},
                    {"tag_name": "c59be28d", "assets": [{"name": "firmware.json", "browser_download_url": "x"}]}]""",
            ),
        )
        val latest = updates.latest()!!
        assertEquals(31, latest.versionCode)
        assertEquals("Faster", latest.notes)
        assertEquals("/repos/alemser/device-link/releases?per_page=10", server.takeRequest().path)

        server.enqueue(MockResponse().setBody("APK BYTES"))
        val dir = Files.createTempDirectory("updates").toFile()
        val file = updates.download(latest, dir)
        assertEquals("devicelink-31.apk", file.name)
        assertEquals("APK BYTES", file.readText())
    }

    @Test
    fun noReleaseIsNoUpdate() = runBlocking {
        server.enqueue(MockResponse().setBody("[]"))
        assertNull(updates.latest())
    }
}
