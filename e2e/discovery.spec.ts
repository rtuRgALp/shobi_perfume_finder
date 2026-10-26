import { test, expect } from "@playwright/test";

test("apostrophes appear in search and details, and shopping links have no preset options", async ({
  page,
}) => {
  await page.goto("/#/?q=Angels%20Share");
  const card = page.locator(".perfume-card").filter({ hasText: "1508-KIL" });
  await expect(card.locator("h3")).toHaveText("Angels' Share");
  await card.locator("h3 a").click();
  await expect(
    page.getByRole("heading", { name: "Angels' Share", exact: true }),
  ).toBeVisible();
  await expect(page).toHaveTitle(
    "Angels' Share by By Kilian — Shobi Perfume Finder",
  );
  const shoppingLink = page.getByRole("link", {
    name: "View on Shobi",
    exact: false,
  });
  await expect(shoppingLink).toHaveAttribute(
    "href",
    "https://leparfum.com.gr/en/fragrances-for-women/1508-kil-wp",
  );
  await page.goto("/#/perfume/shobi-5025");
  await expect(
    page.getByRole("heading", {
      name: "Angels' Share On The Rocks",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "View on Shobi", exact: false }),
  ).toHaveAttribute("href", /^[^#]+$/);
});

test("browser history restores URL-backed sorting and search", async ({
  page,
}) => {
  await page.goto("/#/?q=525-DRC&sort=name");
  await expect(page.locator(".perfume-card")).toHaveCount(1);
  await page
    .getByRole("combobox", { name: "Sort fragrances" })
    .selectOption("brand");
  await expect(
    page.getByRole("combobox", { name: "Sort fragrances" }),
  ).toHaveValue("brand");
  await page.goBack();
  await expect(
    page.getByRole("combobox", { name: "Sort fragrances" }),
  ).toHaveValue("name");
  await expect(
    page.getByRole("searchbox", { name: "Search fragrances", exact: true }),
  ).toHaveValue("525-DRC");
});

test("favorites remain usable when browser storage is blocked", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Storage.prototype.setItem = () => {
      throw new DOMException("Storage blocked", "SecurityError");
    };
  });
  await page.goto("/");
  await expect(page.locator(".perfume-card")).toHaveCount(24);
  await page
    .locator(".perfume-card")
    .first()
    .getByRole("button", { name: /Save .* to favorites/ })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Favorites are saved for this visit.",
  );
  await page.getByRole("button", { name: /Favorites/ }).click();
  await expect(page.locator(".perfume-card")).toHaveCount(1);
});

test("catalog, aliases, details, missing guide and direct links", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Perfume catalog" }),
  ).toBeVisible();
  await expect(page.locator(".perfume-card")).toHaveCount(24);
  await page
    .getByRole("searchbox", { name: "Search fragrances", exact: true })
    .fill("525-DRC");
  await expect(page.locator(".perfume-card")).toHaveCount(1);
  await expect(page.locator(".product-code")).toHaveText("1074-DRC");
  await page.route("**/profiles/shobi-*.json", async (route) => {
    const response = await route.fetch();
    const profile = await response.json();
    profile.accords = [];
    profile.evidence.accords = {
      source: null,
      status: "missing",
      retrievedAt: null,
      note: null,
    };
    await route.fulfill({ response, json: profile });
  });
  await page.locator(".card-copy h3 a").click();
  await expect(
    page.getByRole("heading", { name: "Essence Boost Guide" }),
  ).toBeVisible();
  await expect(
    page.getByText("Not enough information for a recommendation."),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "View on Shobi", exact: false }),
  ).toHaveAttribute("href", /^https:\/\/leparfum\.com\.gr\//);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Essence Boost Guide" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Back to discovery" }).click();
  await expect(
    page.getByRole("searchbox", { name: "Search fragrances", exact: true }),
  ).toHaveValue("525-DRC");
  expect(errors).toEqual([]);
});

test("reviewed identity corrections never show another perfume's notes or bottle", async ({
  page,
}) => {
  await page.goto("/#/perfume/shobi-259");
  await expect(
    page.getByRole("heading", {
      name: "L'Eau d'Issey Pour Homme",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Read about the original on Fragrantica" }),
  ).toHaveAttribute("href", /721\.html$/);
  await expect(
    page.getByText("Main Notes are not yet available.", { exact: true }),
  ).toBeVisible();
  await expect(page.locator('img[src$="79.avif"]')).toHaveCount(0);
  await expect(page.locator(".boost-amounts strong")).toHaveText([
    "+2ml",
    "+3–4ml",
    "+5ml",
  ]);
});

test("favorites persist and compose with search", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".perfume-card")).toHaveCount(24);
  const card = page.locator(".perfume-card").first();
  const name = await card.locator("h3").innerText();
  await card.getByRole("button", { name: /Save .* to favorites/ }).click();
  await page.getByRole("button", { name: /Favorites/ }).click();
  await expect(page.locator(".perfume-card")).toHaveCount(1);
  await page.reload();
  await expect(page.locator(".perfume-card")).toHaveCount(1);
  await expect(page.locator(".perfume-card h3")).toHaveText(name);
  await page
    .getByRole("searchbox", { name: "Search fragrances", exact: true })
    .fill("impossible fragrance xyz");
  await expect(page.locator(".perfume-card")).toHaveCount(0);
  await page.getByRole("button", { name: "Clear search & filters" }).click();
  await expect(page.locator(".perfume-card")).toHaveCount(1);
});

test("profiles show useful information without project commentary", async ({
  page,
}) => {
  let originalNotes: string[] = [];
  const apiRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().startsWith("https://api.fragella.com/"))
      apiRequests.push(request.url());
  });
  await page.route("**/profiles/shobi-*.json", async (route) => {
    const response = await route.fetch();
    const profile = await response.json();
    originalNotes = profile.mainNotes.map((n: { name: string }) => n.name);
    const evidence = {
      source: "https://api.fragella.com/docs.html",
      status: "provider",
      retrievedAt: "2026-10-24T00:00:00Z",
      note: "May include estimates.",
    };
    profile.accords = ["amber", "citrus"];
    profile.evidence.accords = evidence;
    profile.longevity = {
      label: "Long Lasting",
      scale: "Fragella descriptive assessment",
      votes: null,
    };
    profile.evidence.longevity = evidence;
    await route.fulfill({ response, json: profile });
  });
  await page.goto("/");
  await expect(page.locator(".perfume-card")).toHaveCount(24);
  await page.locator(".card-copy h3 a").first().click();
  await expect(page.getByText("Long Lasting", { exact: true })).toBeVisible();
  await expect(page.locator("main")).not.toContainText(
    /Fragella|Inherited project guidance|original-v1|Sources & data confidence|Social Card|source evidence|source information conflicts/,
  );
  await expect(page.locator(".boost-amounts strong")).toHaveText([
    "+2ml",
    "+3–4ml",
    "+5ml",
  ]);
  await expect(page.locator(".detail-notes span")).toHaveText(originalNotes);
  expect(apiRequests).toEqual([]);
});

test("mobile filters have a keyboard accessible dialog and no overflow", async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, "Mobile sheet");
  await page.goto("/");
  await expect(page.locator(".perfume-card")).toHaveCount(24);
  await page.getByRole("button", { name: "Filters", exact: true }).click();
  const sheet = page.getByRole("dialog");
  await expect(sheet).toBeVisible();
  await sheet
    .getByRole("searchbox", { name: "Search brand filters" })
    .fill("Diptyque");
  await sheet.getByLabel("Diptyque", { exact: true }).check();
  await sheet.getByRole("button", { name: /Show .* fragrances/ }).click();
  await expect(sheet).not.toBeVisible();
  await expect(page.locator(".card-brand").first()).toHaveText("Diptyque");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("corrupt storage, missing images and unavailable catalog fail gracefully", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("shobi-favorites", "{bad json"),
  );
  await page.route("**/assets/perfumes/**", (route) => route.abort());
  await page.goto("/");
  await expect(page.locator(".perfume-card")).toHaveCount(24);
  await expect(page.getByText("Image unavailable").first()).toBeVisible();
  await page.route("**/data/current.json", (route) => route.abort());
  await page.reload();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await page.unroute("**/data/current.json");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.locator(".perfume-card")).toHaveCount(24);
});
