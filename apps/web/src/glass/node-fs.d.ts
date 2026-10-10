// The glass contrast test reads CSS as plain text with node:fs. Declare just that call instead of
// adding @types/node as a dependency for one test file.
declare module "node:fs" {
  export function readFileSync(path: URL | string, encoding: "utf8"): string;
}
