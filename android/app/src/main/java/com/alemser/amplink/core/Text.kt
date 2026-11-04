package com.alemser.amplink.core

import java.text.Normalizer
import java.util.Locale

/** What the LCD can show, cut to one line: accents go (`ã` → `a`), and its ROM turns `\` into `¥`. */
fun lcdText(text: String, columns: Int): String =
    Normalizer.normalize(text, Normalizer.Form.NFD).filter { it in ' '..'}' && it != '\\' }.take(columns)

fun isIpv4(text: String): Boolean {
    val parts = text.split(".")
    return parts.size == 4 && parts.all { part ->
        part.isNotEmpty() && part.all(Char::isDigit) && (part.toIntOrNull() ?: 256) < 256
    }
}

/** A boot-screen line as the amp draws it: centred. */
fun centred(text: String, columns: Int): String =
    (" ".repeat((columns - text.length).coerceAtLeast(0) / 2) + text).padEnd(columns)

fun decibels(value: Double?, signed: Boolean = false): String = when {
    value == null -> "—"
    signed && value > 0 -> String.format(Locale.US, "+%.0f dB", value)
    signed -> String.format(Locale.US, "%.0f dB", value)
    else -> String.format(Locale.US, "%.2f dB", value)
}

fun balanceText(balance: Balance?): String = when {
    balance == null -> "—"
    balance.db == 0.0 -> "Centre"
    else -> String.format(Locale.US, "%s %.2f", balance.side.orEmpty(), balance.db).trim()
}

/** "2 h 05 min", "42 s". */
fun duration(seconds: Long?): String = when {
    seconds == null -> "—"
    seconds < 60 -> "$seconds s"
    seconds < 3600 -> "${seconds / 60} min"
    else -> String.format(Locale.US, "%d h %02d min", seconds / 3600, seconds % 3600 / 60)
}
