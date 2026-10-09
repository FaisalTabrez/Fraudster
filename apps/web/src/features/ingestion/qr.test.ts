import { BrowserQRCodeReader } from "@zxing/browser";
import { BarcodeFormat, QRCodeWriter } from "@zxing/library";
import { afterEach, describe, expect, it, vi } from "vitest";
import { decodeQr } from "./qr";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function fakeImage(width = 100, height = 100, invalid = false) {
  const image = { naturalWidth: width, naturalHeight: height, onload: null as null | (() => void),
    onerror: null as null | (() => void), removeAttribute: vi.fn(),
    set src(_value: string) { queueMicrotask(() => invalid ? image.onerror?.() : image.onload?.()); } };
  vi.stubGlobal("Image", class { constructor() { return image; } });
  const create = vi.fn(() => "blob:synthetic-local-upload");
  const revoke = vi.fn();
  vi.stubGlobal("URL", class extends URL { static createObjectURL = create; static revokeObjectURL = revoke; });
  return { image, create, revoke };
}

describe("local QR adapter", () => {
  it("passes only a local image to decoder and releases the blob without fetching decoded content", async () => {
    const { image, revoke } = fakeImage();
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    const reader = vi.spyOn(BrowserQRCodeReader.prototype, "decodeFromImageElement")
      .mockResolvedValue({ getText: () => "https://example.test/qr" } as never);
    expect(await decodeQr(new File(["synthetic"], "qr.png", { type: "image/png" }))).toBe("https://example.test/qr");
    expect(reader).toHaveBeenCalledWith(image);
    expect(revoke).toHaveBeenCalledWith("blob:synthetic-local-upload");
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each(["invalid", "pixels", "no-code"])("handles %s and releases local image", async kind => {
    const { revoke } = fakeImage(kind === "pixels" ? 5000 : 100, kind === "pixels" ? 4001 : 100, kind === "invalid");
    const reader = vi.spyOn(BrowserQRCodeReader.prototype, "decodeFromImageElement").mockRejectedValue(new Error("decoder error"));
    await expect(decodeQr(new File(["synthetic"], "qr.jpg", { type: "image/jpeg" }))).rejects.toThrow(
      kind === "invalid" ? /Invalid/ : kind === "pixels" ? /20 million/ : /No readable QR/);
    expect(revoke).toHaveBeenCalledOnce();
    if (kind !== "no-code") expect(reader).not.toHaveBeenCalled();
  });
  it.each(["Synthetic plain text", "https://example.test/qr", "upi://pay?pa=synthetic@example"])
    ("actually decodes a synthetic QR pixel image with pinned browser/library packages: %s", text => {
      const size = 240;
      const matrix = new QRCodeWriter().encode(text, BarcodeFormat.QR_CODE, size, size, new Map());
      const pixels = new Uint8ClampedArray(size * size * 4);
      for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
        const index = (y * size + x) * 4;
        pixels[index] = pixels[index + 1] = pixels[index + 2] = matrix.get(x, y) ? 0 : 255;
        pixels[index + 3] = 255;
      }
      // Real ZXing image binarization + QR detection/decoding, with only the
      // DOM canvas pixel adapter supplied by this synthetic test environment.
      const canvas = { width: size, height: size, getContext: () => ({ getImageData: () => ({ data: pixels }) }) };
      expect(new BrowserQRCodeReader().decodeFromCanvas(canvas as unknown as HTMLCanvasElement).getText()).toBe(text);
    });
});
