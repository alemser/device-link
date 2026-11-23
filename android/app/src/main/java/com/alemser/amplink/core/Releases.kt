package com.alemser.amplink.core

import kotlinx.serialization.Serializable
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException

/**
 * The GitHub releases of a repository, as the app reads them: its own (`app-<n>`, [AppUpdate]) and the devices'
 * firmware (`<device>-<version>`, [Updater]) share alemser/device-link's list.
 */
@Serializable
internal data class GithubRelease(
    val tagName: String = "",
    val draft: Boolean = false,
    val body: String? = null,
    val assets: List<GithubAsset> = emptyList(),
)

@Serializable
internal data class GithubAsset(val name: String, val browserDownloadUrl: String)

/**
 * The releases of [repo] that [match], from the first page that has any; empty when none does. GitHub lists the newest
 * first and can't filter by tag, so this pages until one matches: almost always on the first page.
 */
internal suspend fun OkHttpClient.newestReleases(
    api: String,
    repo: String,
    match: (GithubRelease) -> Boolean,
): List<GithubRelease> {
    for (page in 1..RELEASE_PAGES) {
        val body = fetch(Request.Builder().url("$api/repos/$repo/releases?per_page=$RELEASE_PAGE&page=$page").build())
        val releases = decode<List<GithubRelease>>(body)
        val found = releases.filter { !it.draft && match(it) }
        if (found.isNotEmpty()) return found
        if (releases.size < RELEASE_PAGE) break
    }
    return emptyList()
}

/** Whether [repo] has a release tagged [tag]: one request, `404` meaning no. Any other failure is an [IOException]. */
internal suspend fun OkHttpClient.releaseExists(api: String, repo: String, tag: String): Boolean {
    val a = answer(Request.Builder().url("$api/repos/$repo/releases/tags/$tag").build())
    return when {
        a.ok -> true
        a.code == 404 -> false
        else -> throw IOException("GitHub answered ${a.code} for the release $tag")
    }
}

/**
 * Chosen: a small page keeps the usual single request light (a release with its assets is a few KB); 200 releases back
 * at most, well within GitHub's 60 unauthenticated requests an hour.
 */
internal const val RELEASE_PAGE = 10
private const val RELEASE_PAGES = 20
