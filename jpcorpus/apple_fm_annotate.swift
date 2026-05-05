import Foundation
import FoundationModels

struct AnnotationRequest: Decodable {
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
}

struct ShowContext: Decodable {
    let summary: String?
    let characters: [String]?
}

let data = FileHandle.standardInput.readDataToEndOfFile()
let request = try JSONDecoder().decode(AnnotationRequest.self, from: data)
let showSummary = truncated(request.show_context?.summary ?? "", limit: 280)
let showCharacters = Array((request.show_context?.characters ?? []).prefix(12))
let showContextBlock = (request.use_show_context == true && (!showSummary.isEmpty || !showCharacters.isEmpty))
    ? """
Optional show context for understanding names or references only; trust the source text if there is any conflict:
Summary: \(showSummary.isEmpty ? "(none)" : showSummary)
Characters: \(showCharacters.isEmpty ? "(none)" : showCharacters.joined(separator: ", "))

"""
    : ""
let model = SystemLanguageModel.default
guard model.isAvailable else {
    throw NSError(
        domain: "jpcorpus.apple_fm",
        code: 1,
        userInfo: [NSLocalizedDescriptionKey: "Apple Foundation Models is not available."]
    )
}

let instructions = """
You annotate Japanese media examples for Chinese-speaking JLPT learners.
Return strict JSON only, with keys translation_zh, usage_note_zh, scene_description.
Do not wrap the JSON in Markdown.
Only use the provided source blocks. Do not invent setting, genre, speaker identity, or hidden episode facts.
"""

let prompt = """
Annotate this Japanese media example.

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

let session = LanguageModelSession(instructions: instructions)
let response = try await session.respond(to: prompt)
print(response.content)

func truncated(_ value: String, limit: Int) -> String {
    if value.count <= limit {
        return value
    }
    return String(value.prefix(limit)).trimmingCharacters(in: .whitespacesAndNewlines) + "..."
}
