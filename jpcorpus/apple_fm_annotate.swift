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
}

let data = FileHandle.standardInput.readDataToEndOfFile()
let request = try JSONDecoder().decode(AnnotationRequest.self, from: data)
let model = SystemLanguageModel.default
guard model.isAvailable else {
    throw NSError(
        domain: "jpcorpus.apple_fm",
        code: 1,
        userInfo: [NSLocalizedDescriptionKey: "Apple Foundation Models is not available."]
    )
}

let instructions = """
You annotate Japanese subtitle examples for Chinese-speaking JLPT learners.
Return strict JSON only, with keys translation_zh, usage_note_zh, scene_description.
Do not wrap the JSON in Markdown.
Only use the provided subtitle lines. Do not invent setting, genre, speaker identity, or hidden episode facts.
"""

let prompt = """
Annotate this Japanese subtitle example.

Word: \(request.word)
Reading: \(request.reading)
JLPT level: \(request.level)
Chinese meaning: \(request.meaning_zh)
English meaning: \(request.meaning)
Matched text in sentence: \(request.matched_text)

Previous subtitle lines:
\(request.context_before.isEmpty ? "(none)" : request.context_before.joined(separator: "\n"))

Current line:
\(request.sentence)

Next subtitle lines:
\(request.context_after.isEmpty ? "(none)" : request.context_after.joined(separator: "\n"))

Return JSON:
{
  "translation_zh": "natural Chinese translation of the current line only",
  "usage_note_zh": "one short Chinese note explaining the target word's meaning or grammar in this line",
  "scene_description": "one short Chinese description based only on the provided subtitle lines; say unclear if unclear"
}
"""

let session = LanguageModelSession(instructions: instructions)
let response = try await session.respond(to: prompt)
print(response.content)
