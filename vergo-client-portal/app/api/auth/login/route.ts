import { NextRequest, NextResponse } from "next/server";
import { loadClientAccounts, verifyPassword } from "../../../../lib/auth";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const email = String(body.email || "").trim().toLowerCase();
  const password = String(body.password || "");

  if (!email || !password) {
    return NextResponse.json(
      { error: "Please enter both email and password." },
      { status: 400 }
    );
  }

  const accounts = await loadClientAccounts();
  const account = accounts.find((item) => item.email.toLowerCase() === email);

  if (!account || !account.active || !verifyPassword(password, account.passwordHash)) {
    return NextResponse.json(
      { error: "Invalid email or password, or the account is inactive." },
      { status: 401 }
    );
  }

  const response = NextResponse.json({
    success: true,
    client: {
      clientName: account.clientName,
      slug: account.slug,
      email: account.email,
    },
  });

  response.cookies.set("vergo_client_email", account.email, {
    path: "/",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 24 * 7,
  });

  return response;
}
