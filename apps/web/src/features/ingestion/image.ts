export const MAX_IMAGE_BYTES = 5_000_000;
export const MAX_IMAGE_PIXELS = 20_000_000;

export function validateFile(file: File) {
  if (!["image/png", "image/jpeg"].includes(file.type)) throw new Error("Only PNG and JPEG images are supported.");
  if (!file.size) throw new Error("The image is empty.");
  if (file.size > MAX_IMAGE_BYTES) throw new Error("Image exceeds the 5 MB upload limit.");
}

export async function withLocalImage<T>(file: File, use: (image: HTMLImageElement) => Promise<T>): Promise<T> {
  validateFile(file);
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
    return await use(image);
  } finally {
    image.onload = null;
    image.onerror = null;
    image.removeAttribute("src");
    URL.revokeObjectURL(localUrl);
  }
}
