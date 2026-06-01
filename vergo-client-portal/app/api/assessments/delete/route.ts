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

export async function DELETE(request: NextRequest) {
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

    const { assessmentId } = await request.json();

    if (!assessmentId) {
      return NextResponse.json(
        { error: "Assessment ID is required." },
        { status: 400 }
      );
    }

    const drive = await getDriveClient();

    // Delete the assessment folder
    await drive.files.delete({
      fileId: assessmentId,
      supportsAllDrives: true,
    });

    return NextResponse.json({
      success: true,
      message: "Assessment deleted successfully.",
    });
  } catch (error) {
    console.error(error);

    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Failed to delete assessment.",
      },
      { status: 500 }
    );
  }
}
