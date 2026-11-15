import { describe, expect, it } from "vitest";

import { AVATAR_MAX_BYTES, checkAvatarFile } from "./avatar";

describe("checkAvatarFile", () => {
  it("accepte les formats JPEG, PNG et WebP jusqu'à 2 Mo", () => {
    for (const type of ["image/jpeg", "image/png", "image/webp"]) {
      expect(checkAvatarFile({ type, size: AVATAR_MAX_BYTES })).toBeNull();
    }
  });

  it("refuse les autres formats", () => {
    expect(checkAvatarFile({ type: "image/gif", size: 1000 })).toMatch(/Format non accepté/);
    expect(checkAvatarFile({ type: "application/pdf", size: 1000 })).toMatch(/Format non accepté/);
  });

  it("refuse les images de plus de 2 Mo", () => {
    expect(checkAvatarFile({ type: "image/png", size: AVATAR_MAX_BYTES + 1 })).toMatch(/trop lourde/);
  });
});
