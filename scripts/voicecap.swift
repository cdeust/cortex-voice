// cortex-voice native capture helper.
//
// On-device speech capture for the cortex-voice MCP. Records a short utterance
// from the default microphone, transcribes it with Apple's Speech framework
// (on-device when supported), and emits a single JSON object on stdout.
//
// Modes:
//   voicecap --check-auth
//   voicecap --capture [--max-seconds N] [--silence-ms M] [--locale id]
//
// Output (success): {"transcript": "...", "confidence": 0.0-1.0,
//                    "duration": seconds, "on_device": bool}
// Output (auth):    {"speech_auth": "...", "mic_auth": "..."}
// Output (failure): {"error": "message"}  (exit 1)

import AVFoundation
import Foundation
import Speech

func emit(_ obj: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: obj),
        let s = String(data: data, encoding: .utf8)
    {
        print(s)
    }
}

func fail(_ message: String) -> Never {
    emit(["error": message])
    exit(1)
}

func argValue(_ name: String, _ fallback: String) -> String {
    let a = CommandLine.arguments
    if let i = a.firstIndex(of: name), i + 1 < a.count { return a[i + 1] }
    return fallback
}

func requestSpeechAuth() -> String {
    let sem = DispatchSemaphore(value: 0)
    var result = "unknown"
    SFSpeechRecognizer.requestAuthorization { status in
        switch status {
        case .authorized: result = "authorized"
        case .denied: result = "denied"
        case .restricted: result = "restricted"
        case .notDetermined: result = "notDetermined"
        @unknown default: result = "unknown"
        }
        sem.signal()
    }
    sem.wait()
    return result
}

func requestMicAuth() -> String {
    let sem = DispatchSemaphore(value: 0)
    var result = "unknown"
    AVCaptureDevice.requestAccess(for: .audio) { granted in
        result = granted ? "authorized" : "denied"
        sem.signal()
    }
    sem.wait()
    return result
}

// Shared recognition state, guarded by `lock`.
final class CaptureState {
    let lock = NSLock()
    var transcript = ""
    var confidence = 0.0
    var lastUpdate = Date()
    var heard = false
    var done = false
}

func runRecognition(
    recognizer: SFSpeechRecognizer, maxSeconds: Double, silenceMs: Double
) -> (String, Double, Double) {
    let engine = AVAudioEngine()
    let request = SFSpeechAudioBufferRecognitionRequest()
    request.shouldReportPartialResults = true
    let onDevice = recognizer.supportsOnDeviceRecognition
    if onDevice { request.requiresOnDeviceRecognition = true }

    let input = engine.inputNode
    let format = input.outputFormat(forBus: 0)
    input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
        request.append(buffer)
    }
    engine.prepare()
    do { try engine.start() } catch {
        fail("audio engine start failed: \(error.localizedDescription)")
    }

    let state = CaptureState()
    let start = Date()
    let task = recognizer.recognitionTask(with: request) { result, error in
        state.lock.lock()
        defer { state.lock.unlock() }
        if let result = result {
            let text = result.bestTranscription.formattedString
            if !text.isEmpty {
                state.transcript = text
                state.heard = true
                state.lastUpdate = Date()
                let segs = result.bestTranscription.segments
                if !segs.isEmpty {
                    state.confidence =
                        segs.map { Double($0.confidence) }.reduce(0, +) / Double(segs.count)
                }
            }
            if result.isFinal { state.done = true }
        }
        if error != nil { state.done = true }
    }

    let silence = silenceMs / 1000.0
    while true {
        RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.1))
        state.lock.lock()
        let elapsed = Date().timeIntervalSince(start)
        let quiet = Date().timeIntervalSince(state.lastUpdate)
        let finished = state.done || elapsed >= maxSeconds || (state.heard && quiet >= silence)
        state.lock.unlock()
        if finished { break }
    }

    engine.stop()
    input.removeTap(onBus: 0)
    request.endAudio()
    task.cancel()

    state.lock.lock()
    let out = (state.transcript, state.confidence, Date().timeIntervalSince(start))
    state.lock.unlock()
    return out
}

func capture(maxSeconds: Double, silenceMs: Double, localeId: String) -> Never {
    let speech = requestSpeechAuth()
    let mic = requestMicAuth()
    guard speech == "authorized" else { fail("speech recognition not authorized: \(speech)") }
    guard mic == "authorized" else { fail("microphone not authorized: \(mic)") }

    guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: localeId)) else {
        fail("no speech recognizer for locale \(localeId)")
    }
    guard recognizer.isAvailable else { fail("speech recognizer unavailable") }

    let (transcript, confidence, duration) = runRecognition(
        recognizer: recognizer, maxSeconds: maxSeconds, silenceMs: silenceMs)
    emit([
        "transcript": transcript, "confidence": confidence, "duration": duration,
        "on_device": recognizer.supportsOnDeviceRecognition,
    ])
    exit(0)
}

let mode = CommandLine.arguments.dropFirst().first ?? "--capture"
switch mode {
case "--check-auth":
    let speech = requestSpeechAuth()
    let mic = requestMicAuth()
    emit(["speech_auth": speech, "mic_auth": mic])
    exit(0)
case "--capture":
    let maxS = Double(argValue("--max-seconds", "15")) ?? 15
    let silM = Double(argValue("--silence-ms", "1200")) ?? 1200
    let loc = argValue("--locale", "en-US")
    capture(maxSeconds: maxS, silenceMs: silM, localeId: loc)
default:
    fail("unknown mode \(mode)")
}
