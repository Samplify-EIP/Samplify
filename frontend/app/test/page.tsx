'use client'

import { Navbar } from "../../components/navbar";
import { AudioFileUpload } from "../../components/audio-file-upload";

export default function Page() {
    return (
      <main className="bg-black min-h-screen">
        <div>
          <Navbar/>
        </div>
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">Audio File Upload</h1>
            <p className="text-muted-foreground">
              Drag and drop audio files or click to browse. Only audio files (MP3, WAV, OGG, etc.) are accepted.
            </p>
          </div>
          <AudioFileUpload />
        </div>
      </main>
    );
}
