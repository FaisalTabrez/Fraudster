import { withLocalImage } from "./image";

export async function decodeQr(file: File): Promise<string> {
  // Only a locally created blob URL reaches ZXing. Decoded content never
  // becomes an image source, navigation target, or network request.
  return withLocalImage(file, async image => {
    try {
      const { BrowserQRCodeReader } = await import("@zxing/browser");
      const result = await new BrowserQRCodeReader().decodeFromImageElement(image);
      return result.getText();
    } catch {
      throw new Error("No readable QR code found. Try a clearer image containing one QR code.");
    }
  });
}
