import { MAX_IMAGE_PIXELS, validateFile } from "./ingestion";

export async function decodeQr(file: File): Promise<string> {
  validateFile(file);
  // Only a locally created blob URL reaches ZXing. Decoded content never
  // becomes an image source, navigation target, or network request.
  const localUrl = URL.createObjectURL(file);
  const image = new Image();
  try {
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () => reject(new Error("Invalid or damaged image."));
      image.src = localUrl;
    });
    if (!image.naturalWidth || !image.naturalHeight) throw new Error("Invalid or damaged image.");
    if (image.naturalWidth * image.naturalHeight > MAX_IMAGE_PIXELS) {
      throw new Error("Image exceeds the 20 million pixel limit.");
    }
    try {
      const { BrowserQRCodeReader } = await import("@zxing/browser");
      const result = await new BrowserQRCodeReader().decodeFromImageElement(image);
      return result.getText();
    } catch {
      throw new Error("No readable QR code found. Try a clearer image containing one QR code.");
    }
  } finally {
    image.onload = null;
    image.onerror = null;
    image.removeAttribute("src");
    URL.revokeObjectURL(localUrl);
  }
}
