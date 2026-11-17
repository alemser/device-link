package com.alemser.amplink.ui

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.alemser.amplink.BuildConfig
import com.alemser.amplink.core.AppRelease
import com.alemser.amplink.core.AppUpdate
import kotlinx.coroutines.launch
import java.io.File
import java.io.IOException

/**
 * "A new version of the app is available", on the device list, once per start of the app. Nothing shows when the app
 * is up to date or GitHub can't be reached.
 */
@Composable
fun AppUpdateBanner() {
    val context = LocalContext.current
    val updates = remember { AppUpdate() }
    val scope = rememberCoroutineScope()
    var release by remember { mutableStateOf<AppRelease?>(null) }
    var busy by remember { mutableStateOf(false) }
    var note by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(Unit) {
        release = runCatching { updates.latest() }.getOrNull()?.takeIf { it.versionCode > BuildConfig.VERSION_CODE }
    }
    val found = release ?: return
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = MaterialTheme.colorScheme.secondaryContainer,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("App update available", style = MaterialTheme.typography.titleMedium)
                    Hint("Version ${found.versionCode} (this is ${BuildConfig.VERSION_CODE})")
                }
                Button(
                    enabled = !busy,
                    onClick = {
                        busy = true
                        note = null
                        scope.launch {
                            note = try {
                                install(context, updates.download(found, File(context.cacheDir, UPDATES_DIR)))
                            } catch (e: IOException) {
                                e.message ?: "The download failed"
                            } finally {
                                busy = false
                            }
                        }
                    },
                ) { Text(if (busy) "Downloading…" else "Update") }
            }
            note?.let { Hint(it) }
        }
    }
}

/** Hands the APK to Android's installer; returns a note to show, or null. */
private fun install(context: Context, apk: File): String? {
    val pm = context.packageManager
    if (!pm.canRequestPackageInstalls()) {
        // Once: Android asks the person to allow this app to install updates.
        context.startActivity(
            Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${context.packageName}"))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
        )
        return "Allow installs from DeviceLink, then tap Update again"
    }
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", apk)
    context.startActivity(
        Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, "application/vnd.android.package-archive")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK),
    )
    return null
}

private const val UPDATES_DIR = "updates"
