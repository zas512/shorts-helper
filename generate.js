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
  const cleaned = rawScript
    .replace(/\[[^\]]*\]/g, "")
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .trim();
  const words = cleaned.split(/\s+/).filter(Boolean);
  const first3Words = words.slice(0, 3).join("_").toLowerCase();
  return first3Words.length > 0 ? first3Words : "audio_output";
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
  const modelId = process.env.ELEVENLABS_MODEL_ID || "eleven_v3";

  let hadError = false;

  for (let i = 0; i < lines.length; i++) {
    const fileNumber = i + 1;
    const text = lines[i];
    console.log(
      `[${fileNumber}/${lines.length}] Generating ${fileNumber}.mp3: "${text.slice(0, 45)}..."`
    );
    try {
      const audioStream = await elevenlabs.textToSpeech.convert(voiceId, {
        text: text,
        modelId: modelId,
        outputFormat: "mp3_44100_128",
        voiceSettings: {
          stability: 0.35,
          similarityBoost: 0.75,
          style: 0.0,
          useSpeakerBoost: true
        }
      });
      const chunks = [];
      for await (const chunk of audioStream) {
        chunks.push(chunk);
      }
      const destination = path.join(scriptOutputDir, `${fileNumber}.mp3`);
      fs.writeFileSync(destination, Buffer.concat(chunks));
      console.log(`Saved: output/${folderName}/${fileNumber}.mp3\n`);
    } catch (err) {
      hadError = true;
      let errorDetails = "";
      if (err?.body && typeof err.body.getReader === "function") {
        try {
          const reader = err.body.getReader();
          const decoder = new TextDecoder();
          let done = false;
          while (!done) {
            const chunk = await reader.read();
            done = chunk.done;
            if (chunk.value) errorDetails += decoder.decode(chunk.value);
          }
        } catch (_) {}
      } else if (err?.body && typeof err.body === "object") {
        try {
          errorDetails = JSON.stringify(err.body, null, 2);
        } catch (_) {}
      }

      console.error(`\nFailed to generate audio for line ${fileNumber}:`);
      console.error(`- Status code: ${err?.statusCode || err?.status}`);
      console.error(`- Message: ${err?.message}`);
      if (errorDetails) {
        console.error(`- Response body: ${errorDetails}`);
      }
      console.error(`\nStack trace:\n${err?.stack || err}`);
      console.error("\nStopping generation due to error.");
      break;
    }
  }

  if (!hadError) {
    console.log(`All audio files generated and saved to output/${folderName}/ successfully.`);
  } else {
    process.exit(1);
  }
}

await run();
