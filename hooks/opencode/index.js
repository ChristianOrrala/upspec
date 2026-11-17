// upspec's agent hooks for OpenCode 2.x: one small module, no dependency.
// It runs the plugin's own hook_gate.py (raw output) and hands the text to the agent.
// One OpenCode server serves every session, so each event is checked against this plugin's own project.
import { spawn, spawnSync } from "node:child_process"
import { dirname, resolve, sep } from "node:path"
import { fileURLToPath } from "node:url"

const GATE = resolve(dirname(fileURLToPath(import.meta.url)),
  "../../skills/up-bootstrapping-spec-driven-projects/scripts/hook_gate.py")
// The gate's TURN_START_TIMEOUT (seconds) and the general limit.
const TURN_START_SECONDS = 8
const DEFAULT_SECONDS = 30
const WRITING_TOOL = /write|edit|patch/i
// How the end-of-turn texts of upspec's gate and of the A-files hook begin.
const CONTINUATION = /^(Notes for the agent|The work has drifted from the specifications)/

const inside = (directory, project) => {
  if (typeof directory !== "string" || !directory) return false
  const a = resolve(directory)
  return a === project || a.startsWith(project + sep)
}

// Run the gate; resolves { code, text }, never rejects.
const runGate = (project, moment, args, event, seconds) =>
  new Promise((done) => {
    let out = ""
    let finished = false
    const finish = (value) => {
      if (finished) return
      finished = true
      clearTimeout(timer)
      done(value)
    }
    let child
    let timer
    try {
      child = spawn("python3", [GATE, moment, ...args, "--emit", "raw"], {
        cwd: project,
        stdio: ["pipe", "pipe", "ignore"],
      })
      timer = setTimeout(() => {
        try { child.kill("SIGKILL") } catch {}
        finish({ code: 3, text: "" })
      }, seconds * 1000)
      child.stdout.on("data", (chunk) => { out += chunk })
      child.on("error", () => finish({ code: 3, text: "" }))
      child.on("close", (code) => finish({ code: code ?? 3, text: out.trim() }))
      child.stdin.on("error", () => {})
      child.stdin.end(JSON.stringify(event))
    } catch {
      finish({ code: 3, text: "" })
    }
  })

// The same, synchronously: used where OpenCode does not wait for the handler (its event stream), so that the gate
// has finished, and logged, before the process can exit.
const runGateSync = (project, moment, args, event, seconds) => {
  try {
    const done = spawnSync("python3", [GATE, moment, ...args, "--emit", "raw"], {
      cwd: project,
      input: JSON.stringify(event),
      encoding: "utf8",
      timeout: seconds * 1000,
      killSignal: "SIGKILL",
      stdio: ["pipe", "pipe", "ignore"],
    })
    return { code: done.status ?? 3, text: (done.stdout || "").trim() }
  } catch {
    return { code: 3, text: "" }
  }
}

const sessionOf = (e) =>
  e?.data?.sessionID ?? e?.sessionID ?? e?.properties?.sessionID ?? e?.data?.session?.id ?? e?.session?.id ??
  (String(e?.durable?.aggregateID ?? "").startsWith("ses_") ? e.durable.aggregateID : undefined)

const directoryOf = (e) =>
  e?.location?.directory ?? e?.data?.location?.directory ?? e?.data?.directory ?? e?.directory ??
  e?.session?.directory ?? e?.data?.session?.directory

export default {
  id: "upspec",
  async setup(ctx) {
    const project = resolve(ctx.location.directory)
    const started = new Set()
    const stopped = new Set()
    const ac = new AbortController()

    // Which sessions belong to this project. The execution events and the prompt hook carry no location, so the
    // session is looked up (ctx.session.get returns its Info, with its location) once and remembered. A session that
    // cannot be looked up is not ours: the plugin never acts on another project's session.
    const mine = new Map()
    const own = async (e) => {
      const sessionID = sessionOf(e)
      if (!sessionID) return false
      const given = directoryOf(e)
      if (given !== undefined) mine.set(sessionID, inside(given, project))
      if (!mine.has(sessionID)) {
        try {
          const info = await ctx.session.get({ sessionID })
          mine.set(sessionID, inside(info?.location?.directory ?? info?.directory, project))
        } catch {
          return false
        }
      }
      return mine.get(sessionID) === true
    }
    const put = async (sessionID, moment, text) => {
      if (!text) return
      try {
        await ctx.session.instructions.entry.put({ sessionID, key: "upspec-" + moment, value: text })
      } catch {}
    }
    const event = (sessionID, extra = {}) => ({ session_id: sessionID, cwd: project, ...extra })

    void (async () => {
      try {
        for await (const e of ctx.event.subscribe({ signal: ac.signal })) {
          try {
            const sessionID = sessionOf(e)
            if (!sessionID || !(await own(e))) continue
            if (e.type === "session.execution.started" && !started.has(sessionID)) {
              started.add(sessionID)
              const result = runGateSync(project, "session-start", [], event(sessionID), DEFAULT_SECONDS)
              await put(sessionID, "session-start", result.text)
            } else if (e.type === "session.execution.succeeded" && !stopped.has(sessionID)) {
              const result = runGateSync(project, "before-stop", [], event(sessionID), DEFAULT_SECONDS)
              if (result.code === 2 && result.text) {
                stopped.add(sessionID)
                try { await ctx.session.prompt({ sessionID, text: result.text }) } catch {}
              }
            }
          } catch {}
        }
      } catch {}
    })()

    try {
      await ctx.session.hook("prompt", async (ev) => {
        try {
          // A continuation sent by a plugin at the end of a turn (this one's or the A-files') steers the running
          // session; it is not a new request, and waiting on the gate here lost it in OpenCode 2.3.0.
          const prompt = typeof ev?.prompt?.text === "string" ? ev.prompt.text : ""
          if (!prompt.trim() || CONTINUATION.test(prompt)) return
          const sessionID = sessionOf(ev)
          if (!sessionID || !(await own(ev))) return
          const result = await runGate(project, "turn-start", [], event(sessionID), TURN_START_SECONDS)
          if (result.code === 0) await put(sessionID, "turn-start", result.text)
        } catch {}
      })
    } catch {}

    try {
      await ctx.tool.hook("execute.after", async (ev) => {
        try {
          const sessionID = sessionOf(ev)
          if (!sessionID || !(await own(ev))) return
          if (ev.status !== "completed" || !WRITING_TOOL.test(String(ev.tool ?? ""))) return
          const path = ev.input?.filePath ?? ev.input?.path ?? ev.input?.file_path
          if (typeof path !== "string" || !path) return
          const result = await runGate(project, "after-edit", [path],
            event(sessionID, { tool_input: { file_path: path } }), DEFAULT_SECONDS)
          if (result.code !== 3) await put(sessionID, "after-edit", result.text)
        } catch {}
      })
    } catch {}

    return () => ac.abort()
  },
}
