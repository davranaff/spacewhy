/** Fire a controller command from a React callback without an unhandled rejection. */
export function runPlayerCommand(command: Promise<unknown>): void {
  command.catch(() => undefined);
}
