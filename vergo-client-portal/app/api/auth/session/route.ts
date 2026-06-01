import { NextRequest, NextResponse } from "next/server";
import { loadClientAccounts } from "../../../../lib/auth";

export async function GET(request: NextRequest) {
  const email = request.cookies.get("vergo_client_email")?.value;
  if (!email) {
    return NextResponse.json({ client: null });
  }

  const accounts = await loadClientAccounts();
  const account = accounts.find((item) => item.email.toLowerCase() === email.toLowerCase());
  if (!account || !account.active) {
    return NextResponse.json({ client: null });
  }

  return NextResponse.json({
    client: {
      clientName: account.clientName,
      slug: account.slug,
      email: account.email,
    },
  });
}
