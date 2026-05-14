import Foundation
import FoundationModels

struct ExplanationRequest: Decodable {
    let task: String?
    let word: String
    let reading: String
    let level: String
    let meaning_zh: String
    let meaning: String
    let matched_text: String
    let sentence: String
    let context_before: [String]
    let context_after: [String]
    let show_context: ShowContext?
    let use_show_context: Bool?
    let question: String?
}

struct ShowContext: Decodable {
    let summary: String?
    let characters: [String]?
}

struct WorkerResponse: Encodable {
    let ok: Bool
    let content: String?
    let error: String?
}

let model = SystemLanguageModel.default
guard model.isAvailable else {
    throw NSError(
        domain: "jpcorpus.apple_fm",
        code: 1,
        userInfo: [NSLocalizedDescriptionKey: "Apple Foundation Models is not available."]
    )
}

let instructions = """
You help Chinese-speaking Japanese learners understand Japanese media text.
Return strict JSON only.
Do not wrap the JSON in Markdown.
Only use the provided source blocks. Do not invent setting, genre, speaker identity, or hidden episode facts.
"""

if CommandLine.arguments.contains("--jsonl-server") {
    try await runJsonlServer()
} else {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    let request = try JSONDecoder().decode(ExplanationRequest.self, from: data)
    let content = try await explain(request)
    print(content)
}

func runJsonlServer() async throws {
    while let line = readLine() {
        if line.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            continue
        }
        do {
            let data = Data(line.utf8)
            let request = try JSONDecoder().decode(ExplanationRequest.self, from: data)
            let content = try await explain(request)
            emit(WorkerResponse(ok: true, content: content, error: nil))
        } catch {
            emit(WorkerResponse(ok: false, content: nil, error: String(describing: error)))
        }
    }
}

func explain(_ request: ExplanationRequest) async throws -> String {
    let prompt = request.task == "question" ? buildQuestionPrompt(request) : buildPrompt(request)
    let session = LanguageModelSession(instructions: instructions)
    let response = try await session.respond(to: prompt)
    return response.content
}

func buildPrompt(_ request: ExplanationRequest) -> String {
    let showSummary = truncated(request.show_context?.summary ?? "", limit: 280)
    let showCharacters = Array((request.show_context?.characters ?? []).prefix(12))
    let showContextBlock = (request.use_show_context == true && (!showSummary.isEmpty || !showCharacters.isEmpty))
        ? """
Optional show context for understanding names or references only; trust the source text if there is any conflict:
Summary: \(showSummary.isEmpty ? "(none)" : showSummary)
Characters: \(showCharacters.isEmpty ? "(none)" : showCharacters.joined(separator: ", "))

"""
        : ""
    return """
Explain this Japanese media example.

Word: \(request.word)
Reading: \(request.reading)
JLPT level: \(request.level)
Chinese meaning: \(request.meaning_zh)
English meaning: \(request.meaning)
Matched text in sentence: \(request.matched_text)

Previous source blocks:
\(request.context_before.isEmpty ? "(none)" : request.context_before.joined(separator: "\n"))

Current source block:
\(request.sentence)

Next source blocks:
\(request.context_after.isEmpty ? "(none)" : request.context_after.joined(separator: "\n"))

\(showContextBlock)
Return JSON:
{
  "translation_zh": "natural Simplified Chinese translation of the full current source block only; preserve names and question tone; do not omit content; do not translate honorifics like さん as 小姐 or 先生 unless gender/title is explicit",
  "usage_note_zh": "one short Chinese note explaining the target word's meaning or grammar in this source block",
  "scene_description": ""
}
"""
}

func buildQuestionPrompt(_ request: ExplanationRequest) -> String {
    return """
Answer a Chinese-speaking Japanese learner's question about this exact Japanese text.

Word: \(request.word)
Reading: \(request.reading)
JLPT level: \(request.level)
Chinese meaning: \(request.meaning_zh)
English meaning for disambiguation only: \(request.meaning)
Matched text in sentence: \(request.matched_text)

Previous source blocks:
\(request.context_before.isEmpty ? "(none)" : request.context_before.joined(separator: "\n"))

Current source block:
\(request.sentence)

Next source blocks:
\(request.context_after.isEmpty ? "(none)" : request.context_after.joined(separator: "\n"))

Learner question:
\(request.question ?? "")

Return JSON:
{
  "answer_zh": "natural Simplified Chinese answer, at most three sentences; only use the provided text and dictionary meaning; preserve Japanese expressions exactly when quoting them"
}
"""
}

func emit(_ response: WorkerResponse) {
    let encoder = JSONEncoder()
    do {
        let data = try encoder.encode(response)
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data("\n".utf8))
    } catch {
        let fallback = #"{"ok":false,"content":null,"error":"failed to encode worker response"}"#
        FileHandle.standardOutput.write(Data((fallback + "\n").utf8))
    }
}

func truncated(_ value: String, limit: Int) -> String {
    if value.count <= limit {
        return value
    }
    return String(value.prefix(limit)).trimmingCharacters(in: .whitespacesAndNewlines) + "..."
}
