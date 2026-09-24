import dotenv from "dotenv";
import { ElevenLabsClient } from "elevenlabs";
import fs from "node:fs";
import path from "node:path";

dotenv.config();

const apiKey = process.env.ELEVENLABS_API_KEY;
const voiceId = process.env.VOICE_ID;

if (!apiKey || !voiceId) {
  console.error("Error: ELEVENLABS_API_KEY or VOICE_ID is missing in .env");
  process.exit(1);
}

const elevenlabs = new ElevenLabsClient({ apiKey });

function getFolderNameFromScript(rawScript) {
  const cleaned = rawScript.replace(/\[[^\]]*\]/g, "").replace(/[^a-zA-Z0-9]/g, "");
  const first3 = cleaned.slice(0, 3);
  return first3.length > 0 ? first3 : "audio_output";
}

async function run() {
  const scriptPath = path.join(process.cwd(), "script.txt");
  if (!fs.existsSync(scriptPath)) {
    console.error("Error: script.txt file not found!");
    process.exit(1);
  }
  const rawScript = fs.readFileSync(scriptPath, "utf-8");
  const lines = rawScript
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (lines.length === 0) {
    console.log("script.txt is empty.");
    return;
  }
  const folderName = getFolderNameFromScript(rawScript);
  const baseOutputDir = path.join(process.cwd(), "output");
  const scriptOutputDir = path.join(baseOutputDir, folderName);
  if (!fs.existsSync(scriptOutputDir)) {
    fs.mkdirSync(scriptOutputDir, { recursive: true });
  }
  console.log(`Script prefix detected: "${folderName}"`);
  console.log(`Saving audio files to directory: output/${folderName}/`);
  console.log(`Found ${lines.length} lines. Starting generation with ElevenLabs...\n`);
  for (let i = 0; i < lines.length; i++) {
    const fileNumber = i + 1;
    const text = lines[i];
    console.log(
      `[${fileNumber}/${lines.length}] Generating ${fileNumber}.mp3: "${text.slice(0, 45)}..."`
    );
    try {
      const audioStream = await elevenlabs.textToSpeech.convert(voiceId, {
        text: text,
        model_id: "eleven_v3",
        output_format: "mp3_44100_128"
      });
      const chunks = [];
      for await (const chunk of audioStream) {
        chunks.push(chunk);
      }
      const destination = path.join(scriptOutputDir, `${fileNumber}.mp3`);
      fs.writeFileSync(destination, Buffer.concat(chunks));
      console.log(`Saved: output/${folderName}/${fileNumber}.mp3\n`);
    } catch (err) {
      console.error(`Failed to generate audio for line ${fileNumber}:`, err);
    }
  }
  console.log(`All audio files generated and saved to output/${folderName}/ successfully.`);
}

await run();
