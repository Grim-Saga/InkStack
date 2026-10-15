import { InkStackOptions } from "./inkstackOptions";
import { InkStackExec } from "./exec";
import { Thread } from "./thread";
import { ThreadOptions } from "./threadOptions";

/**
 * InkStack is the main class for interacting with the InkStack agent.
 *
 * Use the `startThread()` method to start a new thread or `resumeThread()` to resume a previously started thread.
 */
export class InkStack {
  private exec: InkStackExec;
  private options: InkStackOptions;

  constructor(options: InkStackOptions = {}) {
    const { inkstackPathOverride, env, config, configOverrides } = options;
    this.exec = new InkStackExec(inkstackPathOverride, env, config, configOverrides);
    this.options = options;
  }

  /**
   * Starts a new conversation with an agent.
   * @returns A new thread instance.
   */
  startThread(options: ThreadOptions = {}): Thread {
    return new Thread(this.exec, this.options, options);
  }

  /**
   * Resumes a conversation with an agent based on the thread id.
   * Threads are persisted in ~/.inkstack/sessions.
   *
   * @param id The id of the thread to resume.
   * @returns A new thread instance.
   */
  resumeThread(id: string, options: ThreadOptions = {}): Thread {
    return new Thread(this.exec, this.options, options, id);
  }
}
