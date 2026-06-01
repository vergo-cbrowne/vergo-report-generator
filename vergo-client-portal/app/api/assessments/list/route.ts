import { NextRequest, NextResponse } from "next/server";
import { google } from "googleapis";
import { loadClientAccounts } from "../../../../lib/auth";

export const runtime = "nodejs";

async function getDriveClient() {
  const auth = new google.auth.GoogleAuth({
    keyFile: process.env.GOOGLE_SERVICE_ACCOUNT_FILE,
    scopes: ["https://www.googleapis.com/auth/drive"],
  });

  return google.drive({ version: "v3", auth });
}

export async function GET(request: NextRequest) {
  try {
    const clientEmail = request.cookies.get("vergo_client_email")?.value || "";

    if (!clientEmail) {
      return NextResponse.json(
        { error: "Client login required." },
        { status: 401 }
      );
    }

    const accounts = await loadClientAccounts();
    const account = accounts.find(
      (item) => item.email.toLowerCase() === clientEmail.toLowerCase()
    );

    if (!account) {
      return NextResponse.json(
        { error: "Client session is invalid." },
        { status: 401 }
      );
    }

    if (!account.active) {
      return NextResponse.json(
        { error: "This client account is inactive." },
        { status: 403 }
      );
    }

    const outputFolderId = account.clientOutputFolderId;
    if (!outputFolderId) {
      return NextResponse.json(
        { error: "Client does not have an output folder configured." },
        { status: 500 }
      );
    }

    const drive = await getDriveClient();

    // List folders in the output folder
    const listResponse = await drive.files.list({
      q: `'${outputFolderId}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false`,
      fields: "files(id, name, createdTime, webViewLink)",
      pageSize: 100,
      supportsAllDrives: true,
    });

    const folders = listResponse.data.files || [];

    // Extract assessment data from folder names (YYYY-MM-DD__CLIENT__TASK__ASSESSMENTTYPE)
    const assessments = folders
      .map((folder) => {
        const name = folder.name || "";
        const parts = name.split("__");

        if (parts.length < 4) {
          return null;
        }

        const date = parts[0];
        const client = parts[1];
        const task = parts[2];
        const assessmentType = parts[3];

        // Filter to only REBA and RULA
        if (!["REBA", "RULA"].includes(assessmentType)) {
          return null;
        }

        return {
          id: folder.id,
          name: folder.name,
          date,
          client,
          task,
          assessmentType,
          createdTime: folder.createdTime,
          webViewLink: folder.webViewLink,
          thumbnail: null,
        };
      })
      .filter((item) => item !== null);

    // Try to get thumbnail for each assessment (first file in folder)
    const assessmentsWithThumbnails = await Promise.all(
      assessments.map(async (assessment: any) => {
        try {
          const filesResponse = await drive.files.list({
            q: `'${assessment.id}' in parents and trashed=false`,
            fields: "files(id, thumbnailLink, mimeType)",
            pageSize: 1,
            supportsAllDrives: true,
          });

          const file = filesResponse.data.files?.[0];
          if (file?.thumbnailLink) {
            assessment.thumbnail = file.thumbnailLink;
          }
        } catch (err) {
          // Ignore thumbnail fetch errors
        }

        return assessment;
      })
    );

    return NextResponse.json({
      success: true,
      assessments: assessmentsWithThumbnails,
    });
  } catch (error) {
    console.error(error);

    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Failed to fetch assessments.",
      },
      { status: 500 }
    );
  }
}
