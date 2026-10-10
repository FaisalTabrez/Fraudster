import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IngestionPanel } from "./IngestionPanel";
import { extractScreenshot } from "./ingestion";
import { decodeQr } from "./qr";

vi.mock("./qr", () => ({ decodeQr: vi.fn() }));
vi.mock("./ingestion", async importOriginal => ({
  ...await importOriginal<typeof import("./ingestion")>(), extractScreenshot: vi.fn(),
}));

const upload = () => fireEvent.change(screen.getByLabelText(/Upload PNG/), {
  target: { files: [new File(["synthetic"], "synthetic.png", { type: "image/png" })] },
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });
beforeEach(() => {
  vi.mocked(extractScreenshot).mockResolvedValue({ status: "complete", text: "Synthetic original",
    boxes: [{ text: "Synthetic original", x: 1, y: 2, width: 90, height: 20 }],
    image: { width: 100, height: 50 }, detail: null });
});

describe("ingestion review", () => {
  it("shows OCR text, dimensions and boxes and submits only corrected text on explicit review", async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    render(<IngestionPanel busy={false} onSubmit={submit} />);
    upload();
    const editor = await screen.findByLabelText(/Review and correct extracted text/);
    expect(submit).not.toHaveBeenCalled();
    expect(screen.getByText(/100 × 50 pixels/)).toBeInTheDocument();
    expect(screen.getByText(/x 1, y 2, width 90, height 20/)).toBeInTheDocument();
    fireEvent.change(editor, { target: { value: "Corrected synthetic text" } });
    fireEvent.click(screen.getByRole("button", { name: /Analyze reviewed/ }));
    expect(submit).toHaveBeenCalledWith({ text: "Corrected synthetic text", source: "screenshot", urls: [], messages: [] });
  });

  it("does not silently truncate long OCR content and requires a nonempty correction", async () => {
    render(<IngestionPanel busy={false} onSubmit={vi.fn()} />);
    upload();
    const editor = await screen.findByLabelText(/Review and correct extracted text/);
    fireEvent.change(editor, { target: { value: "x".repeat(10001) } });
    expect(screen.getByRole("button", { name: /Analyze reviewed/ })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(/Shorten it first/);
    fireEvent.change(editor, { target: { value: " " } });
    expect(screen.getByRole("button", { name: /Analyze reviewed/ })).toBeDisabled();
  });

  it("keeps OCR unavailable explicit and clears stale extracted text when a new upload fails", async () => {
    render(<IngestionPanel busy={false} onSubmit={vi.fn()} />);
    upload();
    await screen.findByLabelText(/Review and correct extracted text/);
    vi.mocked(extractScreenshot).mockRejectedValue(new Error("OCR unavailable"));
    upload();
    expect(await screen.findByRole("alert")).toHaveTextContent("OCR unavailable");
    expect(screen.queryByRole("button", { name: /Analyze reviewed/ })).not.toBeInTheDocument();
  });

  it("reviews QR URL as plain text, then sends the URL to the existing callback without navigation", async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    vi.mocked(decodeQr).mockResolvedValue("https://example.test/qr");
    render(<IngestionPanel busy={false} onSubmit={submit} />);
    fireEvent.change(screen.getByLabelText("Image use"), { target: { value: "qr" } });
    upload();
    await screen.findByLabelText(/Review and correct decoded content/);
    expect(submit).not.toHaveBeenCalled();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(extractScreenshot).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Analyze reviewed/ }));
    expect(submit).toHaveBeenCalledWith({ urls: ["https://example.test/qr"], messages: [], source: "qr" });
  });

  it("shows unsupported payment content for review without offering analysis until corrected", async () => {
    vi.mocked(decodeQr).mockResolvedValue("upi://pay?pa=synthetic@example");
    render(<IngestionPanel busy={false} onSubmit={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Image use"), { target: { value: "qr" } });
    upload();
    await screen.findByLabelText(/Review and correct decoded content/);
    expect(screen.getByRole("alert")).toHaveTextContent(/no recipient has been verified/);
    expect(screen.getByRole("button", { name: /Analyze reviewed/ })).toBeDisabled();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("shows undecodable QR errors and no stale review", async () => {
    vi.mocked(decodeQr).mockRejectedValue(new Error("No readable QR code found"));
    render(<IngestionPanel busy={false} onSubmit={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Image use"), { target: { value: "qr" } });
    upload();
    expect(await screen.findByRole("alert")).toHaveTextContent(/No readable QR/);
    expect(screen.queryByRole("button", { name: /Analyze reviewed/ })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText(/Upload PNG/)).not.toBeDisabled());
  });
  it.each(["Note:hello", "Meeting:10am"])("submits reviewed colon text %s without links", async text => {
    const submit = vi.fn().mockResolvedValue(undefined);
    vi.mocked(decodeQr).mockResolvedValue(text);
    render(<IngestionPanel busy={false} onSubmit={submit} />);
    fireEvent.change(screen.getByLabelText("Image use"), { target: { value: "qr" } });
    upload();
    await screen.findByLabelText(/Review and correct decoded content/);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(submit).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Analyze reviewed/ }));
    expect(submit).toHaveBeenCalledWith({ text, urls: [], messages: [], source: "qr" });
  });
});
