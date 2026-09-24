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

async function run() {
  const scriptPath = path.join(process.cwd(), "script.txt");
  const outputDir = path.join(process.cwd(), "output");

  if (!fs.existsSync(scriptPath)) {
    console.error("Error: script.txt file not found!");
    process.exit(1);
  }

  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
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

  console.log(`Found ${lines.length} lines. Starting batch generation with Eleven v3...\n`);

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

      const destination = path.join(outputDir, `${fileNumber}.mp3`);
      fs.writeFileSync(destination, Buffer.concat(chunks));
      console.log(`Saved: output/${fileNumber}.mp3\n`);
    } catch (err) {
      console.error(`Failed to generate scene ${fileNumber}:`, err);
    }
  }

  console.log("All audio files generated successfully.");
}

await run();
