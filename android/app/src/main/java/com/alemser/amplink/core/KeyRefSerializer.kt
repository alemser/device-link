package com.alemser.amplink.core

import kotlinx.serialization.KSerializer
import kotlinx.serialization.SerializationException
import kotlinx.serialization.descriptors.SerialDescriptor
import kotlinx.serialization.json.JsonDecoder
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder
import kotlinx.serialization.json.JsonEncoder

/** A key in `controls` is `"play"` or `{"key": "play", "label": "Play"}` (docs/contract-v2.md, Controls). */
object KeyRefSerializer : KSerializer<KeyRef> {
    override val descriptor: SerialDescriptor = JsonElement.serializer().descriptor

    override fun deserialize(decoder: Decoder): KeyRef {
        val json = decoder as? JsonDecoder ?: throw SerializationException("keys are read from JSON only")
        return when (val element = json.decodeJsonElement()) {
            is JsonPrimitive -> KeyRef(element.content)
            is JsonObject -> KeyRef(
                element["key"]?.jsonPrimitive?.contentOrNull ?: throw SerializationException("a key without \"key\""),
                element["label"]?.jsonPrimitive?.contentOrNull,
            )
            else -> throw SerializationException("a key must be a string or an object")
        }
    }

    override fun serialize(encoder: Encoder, value: KeyRef) {
        val json = encoder as? JsonEncoder ?: throw SerializationException("keys are written as JSON only")
        if (value.label == null) {
            json.encodeJsonElement(JsonPrimitive(value.key))
        } else {
            json.encodeJsonElement(buildJsonObject {
                put("key", value.key)
                put("label", value.label)
            })
        }
    }
}
