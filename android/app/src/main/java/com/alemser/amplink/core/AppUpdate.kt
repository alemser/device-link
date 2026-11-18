package com.alemser.amplink.core

import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * The app updates itself from the GitHub releases of its own repository (alemser/device-link), like the devices'
 * firmware: each release tagged `app-<versionCode>` carries `devicelink-<versionCode>.apk`, built and published by
 * `tools/publish_app.py`. The app compares the tag with its own versionCode; Android's installer does the rest, asking
 * the person to confirm (and, once, to allow installs from this app).
 */
data class AppRelease(val versionCode: Int, val apkUrl: String, val notes: String)

class AppUpdate(
    private val http: OkHttpClient = OkHttpClient.Builder().callTimeout(120, TimeUnit.SECONDS).build(),
    private val api: String = "https://api.github.com",
    private val repo: String = REPO,
) {
    /**
     * The newest app release, or null when there is none (or no APK in it). The devices' firmware releases live in
     * the same repository (`<device>-<version>`), so only the `app-` ones count.
     */
    suspend fun latest(): AppRelease? =
        http.newestReleases(api, repo) { appRelease(it) != null }.mapNotNull(::appRelease).maxByOrNull { it.versionCode }

    private fun appRelease(r: GithubRelease): AppRelease? {
        val code = r.tagName.removePrefix(TAG_PREFIX).toIntOrNull()?.takeIf { r.tagName.startsWith(TAG_PREFIX) }
        val apk = r.assets.firstOrNull { it.name.endsWith(".apk") }
        return if (code != null && apk != null) AppRelease(code, apk.browserDownloadUrl, r.body.orEmpty()) else null
    }

    /** Downloads [release]'s APK into [dir] (the app's cache), replacing an older download. */
    suspend fun download(release: AppRelease, dir: File): File {
        val data = http.fetchBytes(Request.Builder().url(release.apkUrl).build())
        dir.mkdirs()
        dir.listFiles()?.forEach { it.delete() }
        return File(dir, "devicelink-${release.versionCode}.apk").apply { writeBytes(data) }
    }

    companion object {
        const val REPO = "alemser/device-link"
        const val TAG_PREFIX = "app-"
    }
}
