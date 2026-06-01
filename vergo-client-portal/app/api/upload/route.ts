import { NextRequest, NextResponse } from "next/server";
import { google } from "googleapis";
import { Readable } from "stream";
import { loadClientAccounts } from "../../../lib/auth";

export const runtime = "nodejs";

const MAX_VIDEO_SIZE = 100 * 1024 * 1024;

function safeName(value: string) {
  return value
    .replace(/[^a-zA-Z0-9-_ .]/g, "")
    .replace(/\s+/g, "_")
    .slice(0, 90);
}

function normalizeTaskName(value: string) {
  // lowercase, replace spaces with hyphens, remove special characters
  return value
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "")
    .slice(0, 90);
}

function clientSafeName(value: string) {
  // replace spaces with hyphens and strip special characters (preserve case)
  return String(value || "").replace(/\s+/g, "-").replace(/[^a-zA-Z0-9-]/g, "").slice(0, 90);
}

function bufferToStream(buffer: Buffer) {
  const readable = new Readable();
  readable.push(buffer);
  readable.push(null);
  return readable;
}

async function getDriveClient() {
  const auth = new google.auth.GoogleAuth({
    keyFile: process.env.GOOGLE_SERVICE_ACCOUNT_FILE,
    scopes: ["https://www.googleapis.com/auth/drive"],
  });

  return google.drive({ version: "v3", auth });
}

async function createFolder(drive: any, name: string, parentId: string) {
  const res = await drive.files.create({
    requestBody: {
      name,
      mimeType: "application/vnd.google-apps.folder",
      parents: [parentId],
    },
    fields: "id, name",
    supportsAllDrives: true,
  });

  return res.data.id as string;
}

async function uploadFile(
  drive: any,
  parentId: string,
  name: string,
  mimeType: string,
  buffer: Buffer
) {
  const res = await drive.files.create({
    requestBody: {
      name,
      parents: [parentId],
    },
    media: {
      mimeType,
      body: bufferToStream(buffer),
    },
    fields: "id, name, webViewLink",
    supportsAllDrives: true,
  });

  return res.data;
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const clientEmail = request.cookies.get("vergo_client_email")?.value || String(formData.get("clientEmail") || "").trim().toLowerCase();

    if (!clientEmail) {
      return NextResponse.json(
        { error: "Client login required before uploading." },
        { status: 401 }
      );
    }

    const accounts = await loadClientAccounts();
    const account = accounts.find((item) => item.email.toLowerCase() === clientEmail.toLowerCase());
    if (!account) {
      return NextResponse.json(
        { error: "Client session is invalid. Please log in again." },
        { status: 401 }
      );
    }

    if (!account.active) {
      return NextResponse.json(
        { error: "This client account is inactive and cannot upload." },
        { status: 403 }
      );
    }

    const intakeFolderId = account.intakeFolderId;
    if (!intakeFolderId) {
      return NextResponse.json(
        { error: "This client is not configured with a Google Drive intake folder." },
        { status: 500 }
      );
    }

    const taskName = String(formData.get("taskName") || "");
    const siteLocation = String(formData.get("siteLocation") || "");
    const dateVideoTaken = String(formData.get("dateVideoTaken") || "");
    const assessmentType = String(formData.get("assessmentType") || "");
    const taskDescription = String(formData.get("taskDescription") || "");
    const video = formData.get("video") as File | null;

    if (
      !taskName ||
      !siteLocation ||
      !dateVideoTaken ||
      !assessmentType ||
      !taskDescription ||
      !video
    ) {
      return NextResponse.json(
        { error: "Please complete all required fields and upload a video." },
        { status: 400 }
      );
    }

    if (!["video/mp4", "video/quicktime"].includes(video.type)) {
      return NextResponse.json(
        { error: "Video must be MP4 or MOV." },
        { status: 400 }
      );
    }

    if (video.size > MAX_VIDEO_SIZE) {
      return NextResponse.json(
        {
          error:
            "Video is over 100 MB. Please upload a 20–45 second clip or compress the file.",
        },
        { status: 400 }
      );
    }

    const drive = await getDriveClient();

    // normalize names per spec
    const taskNormalized = normalizeTaskName(taskName || "unnamed-task");
    const clientNameSafe = clientSafeName(account.clientName || account.slug || "client");
    const assessmentSafe = String(assessmentType || "Not-Sure").replace(/\s+/g, "-").replace(/[^a-zA-Z0-9-]/g, "");

    const folderName = `${dateVideoTaken}__${clientNameSafe}__${taskNormalized}__${assessmentSafe}`;

    const uploadFolderId = await createFolder(drive, folderName, intakeFolderId);

    const videoBuffer = Buffer.from(await video.arrayBuffer());

    // Rename uploaded video to CLIENT__TASK__ASSESSMENTTYPE.mp4 (use .mp4 extension per spec)
    const videoFileName = `${clientNameSafe}__${taskNormalized}__${assessmentSafe}.mp4`;

    const uploadedVideo = await uploadFile(drive, uploadFolderId, videoFileName, video.type, videoBuffer);

    // metadata.json per spec
    const metadata = {
      clientName: account.clientName || "",
      taskName: taskName || "",
      assessmentType: assessmentType || "",
      uploadedFilename: videoFileName,
      originalFilename: video.name || "",
      uploadedAt: new Date().toISOString(),
    } as Record<string, string>;

    await uploadFile(drive, uploadFolderId, "metadata.json", "application/json", Buffer.from(JSON.stringify(metadata, null, 2), "utf-8"));

    return NextResponse.json({
      success: true,
      message: "Upload complete.",
      folderId: uploadFolderId,
      video: uploadedVideo,
      metadata,
    });
  } catch (error) {
    console.error(error);

    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Upload failed. Please try again." },
      { status: 500 }
    );
  }
}
