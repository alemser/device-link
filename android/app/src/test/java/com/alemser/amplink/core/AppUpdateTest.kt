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
                    {"tag_name": "sp103-c59be28d", "assets": [{"name": "firmware.json", "browser_download_url": "x"}]}]""",
            ),
        )
        val latest = updates.latest()!!
        assertEquals(31, latest.versionCode)
        assertEquals("Faster", latest.notes)
        assertEquals("/repos/alemser/device-link/releases?per_page=100", server.takeRequest().path)

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

/** Where the app finds a device's firmware: `/device` `firmware` (docs/contract-v2.md, Updates). */
class FirmwareReleaseTest {
    private lateinit var server: MockWebServer
    private lateinit var updater: Updater

    @Before
    fun start() {
        server = MockWebServer()
        server.start()
        updater = Updater(api = server.url("").toString().trimEnd('/'))
    }

    @After
    fun stop() = server.shutdown()

    @Test
    fun aDeviceInTheSharedRepositoryGetsItsNewestTaggedRelease() = runBlocking {
        val manifest = server.url("/sp103-firmware.json").toString()
        server.enqueue(
            MockResponse().setBody(
                """[{"tag_name": "app-31", "assets": [{"name": "devicelink-31.apk", "browser_download_url": "x"}]},
                    {"tag_name": "sp103-aaaa1111", "draft": true, "assets": []},
                    {"tag_name": "cds300-bbbb2222", "assets": [{"name": "firmware.json", "browser_download_url": "x"}]},
                    {"tag_name": "sp103-c59be28d", "assets": [{"name": "firmware.json", "browser_download_url": "$manifest"},
                                                             {"name": "web.py", "browser_download_url": "w"}]},
                    {"tag_name": "sp103-00000000", "assets": [{"name": "firmware.json", "browser_download_url": "x"}]}]""",
            ),
        )
        server.enqueue(MockResponse().setBody("""{"version": "c59be28d", "files": {"web.py": "abc"}}"""))
        val (release, assets) = updater.latest("alemser/device-link/sp103")
        assertEquals("c59be28d", release.version)
        assertEquals("w", assets["web.py"])
        assertEquals("/repos/alemser/device-link/releases?per_page=100", server.takeRequest().path)
        assertEquals("/sp103-firmware.json", server.takeRequest().path)
    }

    @Test
    fun aBridgeFromBeforeTheMoveStillReadsItsOwnRepository() = runBlocking {
        val manifest = server.url("/old.json").toString()
        server.enqueue(MockResponse().setBody("""{"tag_name": "06576747", "assets": [{"name": "firmware.json", "browser_download_url": "$manifest"}]}"""))
        server.enqueue(MockResponse().setBody("""{"version": "06576747", "files": {}}"""))
        assertEquals("06576747", updater.latest("alemser/sp103-mod").first.version)
        assertEquals("/repos/alemser/sp103-mod/releases/latest", server.takeRequest().path)
    }
}
