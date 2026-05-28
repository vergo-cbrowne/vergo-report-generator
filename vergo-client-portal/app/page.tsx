```tsx
'use client';

import { useState } from 'react';

export default function VergoClientUploadPortalMockup() {
  const [uploadComplete, setUploadComplete] = useState(false);

  const uploads = [
    {
      task: 'Drywall Install – Wall Jig',
      date: '2026-05-20',
      method: 'RULA',
      file: 'eastcut_drywall_install_01.mp4',
      size: '82 MB',
      status: 'Ready',
    },
    {
      task: 'Shingling',
      date: '2026-05-21',
      method: 'Unsure',
      file: 'eastcut_shingling_01.mov',
      size: '64 MB',
      status: 'Needs Notes',
    },
  ];

  return (
    <div className="min-h-screen bg-black text-white flex font-sans">
      <aside className="w-80 bg-zinc-950 border-r border-zinc-800 p-6 flex flex-col justify-between">
        <div>
          <div className="mb-10">
            <div className="text-green-400 uppercase tracking-[0.2em] text-xs font-bold mb-3">
              Vergo Client Portal
            </div>

            <h1 className="text-3xl font-light tracking-tight">
              Eastcut Uploads
            </h1>

            <p className="text-zinc-400 text-sm mt-3 leading-relaxed">
              Upload ergonomic assessment videos, provide task context,
              and track report processing.
            </p>
          </div>

          <div className="space-y-3">
            <button className="w-full bg-green-600 hover:bg-green-500 transition rounded-xl px-4 py-3 text-left font-semibold shadow-lg shadow-green-900/30">
              + Upload New Assessment
            </button>

            <button className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-left hover:bg-zinc-800 transition">
              Uploaded Assessments
            </button>

            <button className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-left hover:bg-zinc-800 transition">
              Processing Status
            </button>

            <button className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-left hover:bg-zinc-800 transition">
              Completed Reports
            </button>
          </div>

          <div className="mt-10 bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
            <div className="text-sm font-semibold mb-2">
              Upload Rules
            </div>

            <ul className="text-zinc-400 text-sm space-y-2 leading-relaxed">
              <li>• Maximum 100 MB per video</li>
              <li>• MP4 and MOV formats only</li>
              <li>• Task name required</li>
              <li>• Date video taken required</li>
              <li>• Task description required</li>
              <li>• Assessment type required</li>
            </ul>
          </div>
        </div>

        <div className="border border-zinc-800 rounded-2xl p-4 bg-zinc-900">
          <div className="text-sm text-zinc-400">
            Logged in as
          </div>

          <div className="text-lg font-semibold mt-1">
            Eastcut Safety Team
          </div>

          <div className="text-green-400 text-sm mt-2">
            ● Secure Client Access
          </div>
        </div>
      </aside>

      <main className="flex-1 p-10 overflow-auto">
        <div className="border-b border-zinc-800 pb-8 mb-8">
          <div className="text-green-400 uppercase tracking-[0.2em] text-xs font-bold mb-4">
            Ergonomic Assessment Intake
          </div>

          <h2 className="text-6xl font-light tracking-tight mb-5">
            Upload Assessment Video
          </h2>

          <p className="text-zinc-400 max-w-3xl text-lg leading-relaxed">
            Upload a task video and provide the context Vergo needs
            to generate a clearer ergonomic assessment report.
          </p>
        </div>

        <div className="grid grid-cols-4 gap-5 mb-8">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <div className="text-zinc-400 text-xs uppercase tracking-wider mb-2">
              Uploaded Today
            </div>

            <div className="text-4xl font-bold">6</div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <div className="text-zinc-400 text-xs uppercase tracking-wider mb-2">
              Processing
            </div>

            <div className="text-4xl font-bold text-blue-400">
              2
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <div className="text-zinc-400 text-xs uppercase tracking-wider mb-2">
              Reports Complete
            </div>

            <div className="text-4xl font-bold text-green-400">
              14
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <div className="text-zinc-400 text-xs uppercase tracking-wider mb-2">
              Needs Review
            </div>

            <div className="text-4xl font-bold text-orange-400">
              1
            </div>
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-8 shadow-2xl mb-10">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h3 className="text-2xl font-semibold">
                New Task Upload
              </h3>

              <p className="text-zinc-400 mt-2">
                Submit one task video with supporting metadata.
              </p>
            </div>

            <div className="bg-zinc-950 border border-zinc-700 rounded-xl px-4 py-2 text-sm text-zinc-300">
              Max File Size: 100 MB
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-sm text-zinc-400 mb-2">
                Task Name *
              </label>

              <input
                className="w-full bg-black border border-zinc-700 rounded-xl px-4 py-3 outline-none focus:border-green-500"
                placeholder="Drywall Install – Wall Jig"
              />
            </div>

            <div>
              <label className="block text-sm text-zinc-400 mb-2">
                Date Video Taken *
              </label>

              <input
                type="date"
                className="w-full bg-black border border-zinc-700 rounded-xl px-4 py-3 outline-none focus:border-green-500"
              />
            </div>
          </div>

          <div className="mb-6">
            <label className="block text-sm text-zinc-400 mb-2">
              Assessment Type *
            </label>

            <select className="w-full bg-black border border-zinc-700 rounded-xl px-4 py-3 outline-none focus:border-green-500 text-white">
              <option>Select assessment type</option>

              <option>
                REBA — Full body assessment
              </option>

              <option>
                RULA — Upper limb assessment
              </option>

              <option>
                Unsure — Let Vergo determine the assessment method
              </option>
            </select>
          </div>

          <div className="mb-6">
            <label className="block text-sm text-zinc-400 mb-2">
              Task Description *
            </label>

            <textarea
              rows={4}
              className="w-full bg-black border border-zinc-700 rounded-xl px-4 py-3 outline-none focus:border-green-500"
              placeholder="Describe the task, movement patterns, work conditions, tools used, frequency, awkward postures, or worker concerns."
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm text-zinc-400 mb-2">
              Additional Notes / SOP Upload Optional
            </label>

            <div className="border-2 border-dashed border-zinc-700 rounded-2xl p-6 text-center bg-black hover:border-green-500 transition">
              <div className="text-zinc-300 font-medium mb-2">
                Upload DOCX, TXT, or PDF
              </div>

              <div className="text-zinc-500 text-sm">
                Drag and drop or browse files
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm text-zinc-400 mb-2">
              Upload Video *
            </label>

            <div className="border-2 border-dashed border-green-600 rounded-3xl p-12 text-center bg-black hover:bg-zinc-950 transition">
              <div className="text-2xl mb-3">⬆</div>

              <div className="text-lg font-semibold mb-2">
                Drag and drop video here
              </div>

              <div className="text-zinc-400 text-sm mb-4">
                MP4 or MOV • Maximum 100 MB
              </div>

              <button className="bg-green-600 hover:bg-green-500 transition rounded-xl px-6 py-3 font-semibold shadow-lg shadow-green-900/30">
                Browse Files
              </button>
            </div>
          </div>

          {uploadComplete && (
            <div className="mt-8 bg-green-500/10 border border-green-500/40 rounded-2xl p-5 flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-green-500/20 text-green-400 flex items-center justify-center text-xl font-bold">
                ✓
              </div>

              <div>
                <div className="text-green-400 font-semibold text-lg">
                  Upload complete
                </div>

                <div className="text-zinc-400 mt-1 leading-relaxed">
                  Your task video and details have been submitted
                  to Vergo successfully.
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end mt-8">
            <button
              onClick={() => setUploadComplete(true)}
              className="bg-green-600 hover:bg-green-500 transition rounded-2xl px-8 py-4 text-lg font-semibold shadow-xl shadow-green-900/30"
            >
              {uploadComplete
                ? 'Upload Complete ✓'
                : 'Submit Task Upload'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
```
