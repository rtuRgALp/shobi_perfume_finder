import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { resolve, extname } from "node:path";
import { test, expect } from "@playwright/test";

test("production deep links and assets work under a repository subdirectory", async ({
  page,
}) => {
  const root = resolve("dist");
  const types: Record<string, string> = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".avif": "image/avif",
    ".webp": "image/webp",
  };
  const server = createServer(async (request, response) => {
    const path = new URL(request.url || "/", "http://localhost").pathname;
    const file = resolve(root, path.slice("/Shobi/".length) || "index.html");
    if (!path.startsWith("/Shobi/") || !file.startsWith(root + "/")) {
      response.writeHead(404).end();
      return;
    }
    try {
      response.writeHead(200, {
        "Content-Type": types[extname(file)] || "application/octet-stream",
      });
      response.end(await readFile(file));
    } catch {
      response.writeHead(404).end();
    }
  });
  await new Promise<void>((done) => server.listen(0, "127.0.0.1", done));
  const address = server.address();
  if (!address || typeof address === "string")
    throw new Error("Preview unavailable");
  try {
    await page.goto(`http://127.0.0.1:${address.port}/Shobi/#/?q=525-DRC`);
    await expect(page.locator(".perfume-card")).toHaveCount(1);
    await page.locator(".card-copy h3 a").click();
    await expect(
      page.getByRole("heading", { name: "Essence Boost Guide" }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Essence Boost Guide" }),
    ).toBeVisible();
  } finally {
    await new Promise<void>((done, reject) =>
      server.close((error) => (error ? reject(error) : done())),
    );
  }
});
