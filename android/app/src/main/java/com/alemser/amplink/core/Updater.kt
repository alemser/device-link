package com.alemser.amplink.core

import kotlinx.coroutines.delay
import kotlinx.serialization.Serializable
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

/**
 * Firmware updates from the app (docs/contract-v2.md, "Updates from the app"). A device names where its firmware is
 * released in `/device` `firmware`: `owner/repo/device` means the newest release of `owner/repo` tagged
 * `<device>-<version>` (alemser/device-link/sp103 → sp103-…); a bare `owner/repo` (a bridge from before 2026-11-17)
 * means that repository's latest release. Either carries `firmware.json` and the files.
 * The bridge side is ota.py: stage the files that differ, delete the ones the release dropped, apply, and follow
 * `GET /update` until the bridge confirms the new version or rolls back by itself.
 */
@Serializable
data class Release(val version: String, val files: Map<String, String>)

/** The firmware place has no release for this device: not a failure, just nothing to offer. */
class NoRelease(message: String) : IOException(message)

/**
 * What the firmware screen offers a device, given the newest release (docs/contract-v2.md, Updates step 2). Versions
 * are content hashes and can't be ordered, so the releases order them: a release is newer only than an older release.
 */
enum class Offer {
    /** The device runs the newest release. */
    UP_TO_DATE,

    /** The device runs an older release (or doesn't say which): the newest is offered. */
    UPDATE,

    /** The device runs a version no release has, sent from a computer: newer than every release, nothing offered. */
    AHEAD,
}

/** [Offer] for a device running [running], the newest release being [newest]; [isRelease] says whether [running] is. */
fun offer(running: String?, newest: String, isRelease: Boolean): Offer = when {
    running == newest -> Offer.UP_TO_DATE
    running == null || isRelease -> Offer.UPDATE
    else -> Offer.AHEAD
}

/** The newest release for a device, the URL of each of its assets, and what to offer. */
data class Check(val release: Release, val assets: Map<String, String>, val offer: Offer)

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
    /** The newest firmware release for [firmware] (`/device` `firmware`), with the URL of each asset. */
    suspend fun latest(firmware: String): Pair<Release, Map<String, String>> {
        val parts = firmware.split('/')
        val release = when (parts.size) {
            2 -> decode<GithubRelease>(http.fetch(Request.Builder().url("$api/repos/$firmware/releases/latest").build()))
            3 -> newest(parts[0] + "/" + parts[1], parts[2] + "-")
            else -> throw IOException("Not a firmware place: $firmware")
        }
        val assets = release.assets.associate { it.name to it.browserDownloadUrl }
        val manifest = assets["firmware.json"] ?: throw IOException("The release for $firmware has no firmware.json")
        return decode<Release>(http.fetch(Request.Builder().url(manifest).build())) to assets
    }

    /**
     * The newest release for [firmware] and what to offer a device running [running]. In the shared repository a
     * version is a release when the tag `<device>-<version>` exists. A bare `owner/repo` (a bridge from before
     * 2026-11-17) tags its releases otherwise, so any other version is taken for an older release there.
     */
    suspend fun check(firmware: String, running: String?): Check {
        val (release, assets) = latest(firmware)
        val parts = firmware.split('/')
        val isRelease = running != null && running != release.version &&
            (parts.size != 3 || http.releaseExists(api, parts[0] + "/" + parts[1], parts[2] + "-" + running))
        return Check(release, assets, offer(running, release.version, isRelease))
    }

    /** The newest release of [repo] tagged [prefix]… (the app's own and the other devices' share the list). */
    private suspend fun newest(repo: String, prefix: String): GithubRelease =
        http.newestReleases(api, repo) { it.tagName.startsWith(prefix) }.firstOrNull()
            ?: throw NoRelease("No release tagged $prefix… in $repo")

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
        val applied = runCatching { client.updateAction("apply") }   // the answer may be lost as the bridge restarts
        if (applied.isFailure) {
            // Lost, or refused? A bridge that applied is on trial or restarting; one that didn't still has the files.
            val st = runCatching { client.updateStatus() }.getOrNull()
            if (st != null && st.state != "trial" && st.staged.isNotEmpty()) {
                throw IOException("The device didn't apply the update: ${applied.exceptionOrNull()?.message}")
            }
        }
        return await(client, release.version).also(progress)
    }

    private suspend fun await(client: BridgeClient, version: String): UpdateStep {
        repeat(WAIT_S / POLL_S) {
            delay(POLL_S * 1000L)
            val st = runCatching { client.updateStatus() }.getOrNull() ?: return@repeat
            if (st.state == "ok" && st.version == version) return UpdateStep.Done(version)
            // `tried` tells this update's rollback from an older one (a bridge from before 2026-11-18 doesn't say).
            if (st.state == "rolled_back" && (st.tried == null || st.tried == version)) {
                return UpdateStep.RolledBack(st.why ?: "the new version failed")
            }
        }
        return UpdateStep.RolledBack("the device didn't confirm in time; it goes back to the previous version by itself")
    }

    private companion object {
        /** Only over USB: the gatekeeper and the bridge's own secrets (ota.py LOCKED). */
        val LOCKED = setOf("main.py", "secrets.py")

        /** Chosen: the bridge's trial is 180 s (main.py TRIAL_S), plus its restart and Wi-Fi. */
        const val WAIT_S = 270
        const val POLL_S = 2


    }
}

/** A download, as bytes (a firmware file must arrive byte for byte, so not through [fetch]'s text). */
internal suspend fun OkHttpClient.fetchBytes(request: Request): ByteArray {
    val a = answer(request)
    if (!a.ok) throw IOException("Download failed: ${a.code}")
    return a.body
}

internal fun sha256(data: ByteArray): String =
    MessageDigest.getInstance("SHA-256").digest(data).joinToString("") { "%02x".format(it) }
