package com.alemser.amplink.core

import kotlinx.coroutines.delay
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.serialization.Serializable
import okhttp3.Call
import okhttp3.Callback
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import java.io.IOException
import java.security.MessageDigest
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Firmware updates from the app (docs/contract-v2.md, "Updates from the app"). A device names its firmware's GitHub
 * repository in `/device` `firmware`; the latest release of that repository carries `firmware.json` and the files.
 * The bridge side is ota.py: stage the files that differ, delete the ones the release dropped, apply, and follow
 * `GET /update` until the bridge confirms the new version or rolls back by itself.
 */
@Serializable
data class Release(val version: String, val files: Map<String, String>)

/** Where an update stands, for the screen. */
sealed interface UpdateStep {
    data class Sending(val file: String, val done: Int, val total: Int) : UpdateStep
    data object Restarting : UpdateStep
    data class Done(val version: String) : UpdateStep
    data class RolledBack(val why: String) : UpdateStep
}

class Updater(
    private val http: OkHttpClient = OkHttpClient.Builder().callTimeout(30, TimeUnit.SECONDS).build(),
    private val api: String = "https://api.github.com",
) {
    /** The latest release of [repo] ("owner/name"), with the URL of each asset. */
    suspend fun latest(repo: String): Pair<Release, Map<String, String>> {
        val body = http.fetch(Request.Builder().url("$api/repos/$repo/releases/latest").build())
        val assets = decode<GithubRelease>(body).assets.associate { it.name to it.browserDownloadUrl }
        val manifest = assets["firmware.json"] ?: throw IOException("The release of $repo has no firmware.json")
        return decode<Release>(http.fetch(Request.Builder().url(manifest).build())) to assets
    }

    /** Sends [release] to the device at [client], reporting each step; returns the outcome. */
    suspend fun install(
        client: BridgeClient,
        release: Release,
        assets: Map<String, String>,
        progress: (UpdateStep) -> Unit,
    ): UpdateStep {
        val running = client.updateStatus()
        if (running.state == "trial") throw IOException("The last update is still on trial; try again in a few minutes")
        val send = release.files.filter { (name, sha) -> running.files[name] != sha }
        val drop = running.files.keys.filter { it !in release.files && it !in LOCKED }
        client.updateAction("cancel")
        send.keys.forEachIndexed { i, name ->
            progress(UpdateStep.Sending(name, i, send.size))
            val url = assets[name] ?: throw IOException("The release has no $name")
            val data = http.fetchBytes(Request.Builder().url(url).build())
            if (sha256(data) != release.files[name]) throw IOException("$name downloaded corrupted; nothing applied")
            if (client.stage(name, data) != release.files[name]) throw IOException("$name arrived corrupted; nothing applied")
        }
        drop.forEach { client.stageDelete(it) }
        progress(UpdateStep.Restarting)
        runCatching { client.updateAction("apply") }       // the answer may be lost as the bridge restarts
        return await(client, release.version).also(progress)
    }

    private suspend fun await(client: BridgeClient, version: String): UpdateStep {
        repeat(WAIT_S / POLL_S) {
            delay(POLL_S * 1000L)
            val st = runCatching { client.updateStatus() }.getOrNull() ?: return@repeat
            if (st.state == "ok" && st.version == version) return UpdateStep.Done(version)
            if (st.state == "rolled_back") return UpdateStep.RolledBack(st.why ?: "the new version failed")
        }
        return UpdateStep.RolledBack("the device didn't confirm in time; it goes back to the previous version by itself")
    }

    @Serializable
    private data class GithubRelease(val assets: List<Asset> = emptyList())

    @Serializable
    private data class Asset(val name: String, val browserDownloadUrl: String)

    private companion object {
        /** Only over USB: the gatekeeper and the bridge's own secrets (ota.py LOCKED). */
        val LOCKED = setOf("main.py", "secrets.py")

        /** Chosen: the bridge's trial is 180 s (main.py TRIAL_S), plus its restart and Wi-Fi. */
        const val WAIT_S = 270
        const val POLL_S = 2
    }
}

/** A download, as bytes (a firmware file must arrive byte for byte, so not through [fetch]'s text). */
internal suspend fun OkHttpClient.fetchBytes(request: Request): ByteArray = suspendCancellableCoroutine { waiting ->
    val call = newCall(request)
    waiting.invokeOnCancellation { call.cancel() }
    call.enqueue(object : Callback {
        override fun onFailure(call: Call, e: IOException) {
            if (waiting.isActive) waiting.resumeWithException(e)
        }

        override fun onResponse(call: Call, response: Response) {
            val outcome = runCatching {
                response.use {
                    if (!it.isSuccessful) throw IOException("Download failed: ${it.code}")
                    it.body?.bytes() ?: ByteArray(0)
                }
            }
            if (waiting.isActive) outcome.fold(waiting::resume, waiting::resumeWithException)
        }
    })
}

internal fun sha256(data: ByteArray): String =
    MessageDigest.getInstance("SHA-256").digest(data).joinToString("") { "%02x".format(it) }
