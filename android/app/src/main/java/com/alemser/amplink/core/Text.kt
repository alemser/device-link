package com.alemser.amplink.core

import java.text.Normalizer

/** What an LCD can show (a setting with `charset: lcd`), cut to [columns]: accents go (`ã` → `a`), and `\` and `~` too. */
fun lcdText(text: String, columns: Int): String =
    Normalizer.normalize(text, Normalizer.Form.NFD).filter { it in ' '..'}' && it != '\\' }.take(columns)

fun isIpv4(text: String): Boolean {
    val parts = text.split(".")
    return parts.size == 4 && parts.all { part ->
        part.isNotEmpty() && part.all(Char::isDigit) && (part.toIntOrNull() ?: 256) < 256
    }
}
