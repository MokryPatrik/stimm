# AsyncFlow API

## Docs
- [Welcome to AsyncFlow API](https://docs.async.ai/welcome-to-asyncflow-api-990330m0.md): 
- [Get Started](https://docs.async.ai/get-started-990331m0.md): 
- Advanced Guides > Custom Pronunciations [Embedding Custom Phonemes in Async TTS API](https://docs.async.ai/embedding-custom-phonemes-in-async-tts-api-1218596m0.md): 
- Advanced Guides > Custom Pronunciations [Pronouncing digits one‑by‑one](https://docs.async.ai/pronouncing-digits-onebyone-1218635m0.md): 
- Advanced Guides > Custom Pronunciations [Insert Silent Pauses with <break>](https://docs.async.ai/insert-silent-pauses-with-break-1674731m0.md): 
- Integrations [Integrate with Twilio](https://docs.async.ai/integrate-with-twilio-1272833m0.md): 
- Integrations [Pipecat Integration](https://docs.async.ai/pipecat-integration-1320230m0.md): 

## API Docs
- API Reference > API Status [API Status Check](https://docs.async.ai/api-status-check-16699695e0.md): Check the API version and status
- API Reference > Text-to-Speech [Text to Speech (WebSocket)](https://docs.async.ai/text-to-speech-websocket-3477526w0.md): The **Text-to-Speech WebSockets API** streams audio from *partial* text while preserving consistent prosody. Use it when your text arrives **incrementally** (real-time transcription, chat, etc.).  
- API Reference > Text-to-Speech [Text to Speech ](https://docs.async.ai/text-to-speech-18760785e0.md): Generates speech using provided text and voice of your choice and returns audio.
- API Reference > Text-to-Speech [Text to Speech with Word Timestamps](https://docs.async.ai/text-to-speech-with-word-timestamps-18761064e0.md): Generates speech using provided text and voice of your choice and returns audio and word timestamps.
- API Reference > Text-to-Speech [Text to Speech (Stream)](https://docs.async.ai/text-to-speech-stream-16699696e0.md): Generates speech using provided text and voice of your choice and returns audio in a stream.
- API Reference > Voice Management [Clone Voice](https://docs.async.ai/clone-voice-16699697e0.md): Clone your voice from 5 second of audio clip
- API Reference > Voice Management [List Voices](https://docs.async.ai/list-voices-16699698e0.md): List the available voices from the voice library
- API Reference > Voice Management [Get Voice](https://docs.async.ai/get-voice-16699699e0.md): Get the voice from the voice libarary using voice id
- API Reference > Voice Management [Update Voice](https://docs.async.ai/update-voice-16699700e0.md): Update a cloned voice from the voice libarary using voice id
- API Reference > Voice Management [Delete Voice](https://docs.async.ai/delete-voice-16699701e0.md): Delete a cloned voice from the voice libarary using voice id
- API Reference > Voice Management [Get Voice Preview](https://docs.async.ai/get-voice-preview-17837309e0.md): Get the voice preview audio url using voice id


# Get Started

# Getting Started with the Async Text-to-Speech Streaming API

Welcome! This quick-start guide walks you through sending your first request and turning text into real-time audio.

## Prerequisites

- Developer account on [Async](https://app.async.ai/)
- API key
- A command-line HTTP client (examples use cURL; feel free to use Postman, Python requests, etc.)
- ffmpeg (optional, but handy for converting the raw stream to other formats for playback)

---

## Get Your API Key

1. Log in to the Async dashbaord.
2. Navigate to API Keys → Create API Key.
3. Copy the key and store it securely (it starts with sk_).
4. You can export it as an environment variable so it never appears in your shell history:

```bash
export ASYNC_API_KEY="sk_xxxxxxxxxxxxxxxxx"
```



## Make Your First Request

Here’s a simple `curl` command that sends text and receives streamed audio in response:

```bash
curl -X POST https://api.async.ai/text_to_speech/streaming \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: your-api-key" \
  --data '{
    "model_id": "asyncflow_v2.0",
    "transcript": "Welcome to Async, where imagination meets intelligent speech synthesis.",
    "voice": { "mode": "id", "id": "e0f39dc4-f691-4e78-bba5-5c636692cc04" },
    "output_format": {
      "container": "raw",
      "encoding": "pcm_s16le",
      "sample_rate": 44100
    }
  }' --output output.raw
```
  
## Playing or Converting the Stream
The command above stores 44.1 kHz 16-bit mono PCM samples in speech.pcm.

Quick playback (macOS/Linux)
```bash
ffplay -f s16le -ar 44100 output.raw
```

Convert to WAV
```bash
ffmpeg -f s16le -ar 44100 -ac 1 -i output.raw output.wav
```
*Tip: For real-time playback, pipe the cURL output directly into ffplay:*
```bash
curl -L https://api.async.ai/text_to_speech/streaming \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $ASYNC_API_KEY" \
  -d @request.json | ffplay -f s16le -ar 44100 -
```

## Handling Errors


| HTTP Code | Meaning |  Most common fixes |
| --- | --- | --- |
| 401 Unauthorized | Bad or missing X-Api-Key | Check key spelling; confirm it has TTS scope. |
| 429 Too Many Requests | You hit the rate limit. | Wait for the mentioned time and retry (or upgrade plan). |
| 400 Bad Request | Validation error in your JSON. | Validate JSON, field names, and ranges. |
|  |  |  |

Need help? [Ping us](https://async.ai/contact-us) or hop into our developer Discord. Happy building!



# API Status Check

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /:
    get:
      summary: API Status Check
      deprecated: false
      description: Check the API version and status
      tags:
        - API Reference/API Status
      parameters:
        - name: version
          in: header
          description: ''
          required: true
          example: v1
          schema:
            type: string
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties:
                  ok:
                    type: boolean
                  version:
                    type: string
                x-apidog-orders:
                  - ok
                  - version
                required:
                  - ok
                  - version
              example:
                ok: true
                version: v1
          headers: {}
          x-apidog-name: Success
      security: []
      x-apidog-folder: API Reference/API Status
      x-apidog-status: released
      x-run-in-apidog: https://app.apidog.com/web/project/909580/apis/api-16699695-run
components:
  schemas: {}
  securitySchemes: {}
servers: []
security: []

```

# Text to Speech (WebSocket)

> The **Text-to-Speech WebSockets API** streams audio from *partial* text while preserving consistent prosody. Use it when your text arrives **incrementally** (real-time transcription, chat, etc.).  

It may be less suitable when the full text is available upfront (HTTP is simpler / lower-latency) or when you need to prototype quickly (WebSockets are more involved).

---

## Handshake

> **WSS** `wss://api.async.ai/text_to_speech/websocket/ws`

### Path parameters
| Name       | Type   | Required | Description                      |
|------------|--------|----------|----------------------------------|
| `api_key` | string | **Yes**  | Async API key.            |
| `version` | string | **Yes**  | API version  |

---

## Send

<details>
<summary><strong>initializeConnection <code>object</code> — Required</strong></summary>

| Property                           | Type    | Required | Description                                                                                      |
|------------------------------------|---------|----------|--------------------------------------------------------------------------------------------------|
 `model_id`                | string  | **Yes**       | Model ID (example: "asyncflow_v2.0")                                                                     |
| `voice`| object| **Yes**       | Dictionary with keys "mode" and "id". (example: {"mode": "id", "id": "e0f39dc4-f691-4e78-bba5-5c636692cc04"}                                                   |
| `output_format`                       | object  | **No**     |  Dictionary with keys "container" , "encoding", "sample_rate", "bit_rate". Defualts to {container="raw", encoding="pcm_s16le", sample_rate=44100}                                                                   |
    
    
For additional details, see the [Text-to-Speech (Stream)](https://docs.async.ai/text-to-speech-stream-16699696e0) endpoint, which uses almost the same parameters.

    
</details>

<details>
<summary><strong>sendText <code>object</code> — Required</strong></summary>

| Property                 | Type    | Required | Description                                                                                                        |
|--------------------------|---------|----------|--------------------------------------------------------------------------------------------------------------------|
| `transcript`                   | string  | **Yes**  | New text chunk—**always ends with a single space**.                                                                |
| `force` | boolean | **No** | Force the TTS even if there is not enough characters in the buffer. Defaults to False.                                                       |

</details>

<details>
<summary><strong>closeConnection <code>object</code> — Required</strong></summary>

| Property | Type   | Required | Description                 |
|----------|--------|----------|-----------------------------|
| `text`   | string | **Yes**  | **Empty string** to finish. |
</details>

---

## Receive

<details>
<summary><strong>audioOutput <code>object</code> — streamed</strong></summary>

| Field                 | Type   | Required | Description                                                      |
|-----------------------|--------|----------|------------------------------------------------------------------|
| `audio`               | string | **Yes**  | Base-64 audio chunk.                               |
| `final` | boolean | **Yes**       | Whether this is the final response for the request                                  |
</details>

<details>
<summary><strong>finalOutput <code>object</code></strong></summary>

| Field    | Type | Required | Notes                    |
|----------|------|----------|--------------------------|
| `audio`  | string | **Yes**        | Always "".           |
  | `final`| boolean | **Yes**  | Always `true`; generation complete. |
</details>


<details>
<summary><strong>Error Responses <code>object</code></strong></summary>

| Field    | Type | Required | Notes                    |
|----------|------|----------|--------------------------|
| `error_code`  | string | **Yes**    | Error code identifying the type of error           |
| `message`| string | **Yes**  | Human-readable error message |
| `extra`| Object | **No**  | Additional error details |
</details>

---
## Example handshake & message flow

<details>
<summary><strong>Handshake</strong> — GET <code>/text_to_speech/websocket/ws</code></summary>

```http
GET text_to_speech/websocket/ws
HTTP/1.1
Host: api.async.ai
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: …
Sec-WebSocket-Version: 13
api_key: <YOUR_API_KEY>
version: v1
````

</details>
<details>
<summary><strong>↑ (send) initializeConnection</strong> — <code>{"model_id": "asyncflow_v2.0",...</code></summary>

```json
{
  "model_id": "asyncflow_v2.0",
  "voice": {
    "mode": "id",
    "id": "e0f39dc4-f691-4e78-bba5-5c636692cc04"
  },
  "output_format": {
    "container": "raw",
    "encoding": "pcm_f32le",
    "sample_rate": 44100
  }
}
```

</details>
<details>
<summary><strong>↑ (send) sendText</strong> — <code>{"transcript":"Welcome to Async."}</code></summary>

```json
{"transcript":"Welcome to Async."}
```

</details>

<details>
<summary><strong>↑ (send) closeConnection</strong> — <code>{"transcript":""}</code></summary>

```json
{ "text": "" }
```

</details>

<details>
<summary><strong>↓ (receive) audioOutput</strong> — <code>{"audio":"Y3Vya...",...}</code></summary>

```json
{
  "audio": "Y3VyaW91cyBtaW5kcyB0aGluayBhbGlrZSA6KQ==",
  "final": false,
}
```
</details>

<details>
<summary><strong>↓ (receive) finalOutput</strong> — <code>{"audio":"", "final":true}</code></summary>

```json
{ "audio": "", "final": true }
```

</details>




## Path
wss://api.async.ai/text_to_speech/websocket/ws