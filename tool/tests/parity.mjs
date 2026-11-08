// Сверяет блок check из docs/index.html с Python на всей выгрузке. Вход — JSON от parity_dump.py.
// Код проверки вырезается из index.html между метками check:start и check:end.
// Запуск из папки tool: node tests/parity.mjs <файл.json>
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const html = readFileSync(new URL("../../docs/index.html", import.meta.url), "utf8");
const block = html.match(/\/\* === check:start ===[\s\S]*?\*\/([\s\S]*?)\/\* === check:end === \*\//);
if (!block) throw new Error("В docs/index.html нет меток check:start и check:end");
const module = join(mkdtempSync(join(tmpdir(), "dupes-")), "check.mjs");
writeFileSync(module, block[1]);
const { analyse } = await import(pathToFileURL(module));

const { records, groups: expected } = JSON.parse(readFileSync(process.argv[2], "utf8"));
const actual = analyse(records);
const show = g => JSON.stringify(g);
const py = new Map(expected.map(g => [g.gid, show(g)]));
const js = new Map(actual.map(g => [g.gid, show(g)]));
let differ = 0;
for (const gid of new Set([...py.keys(), ...js.keys()])) {
  if (py.get(gid) !== js.get(gid)) {
    if (differ++ < 10) console.log(gid, "\n  py:", py.get(gid), "\n  js:", js.get(gid));
  }
}
console.log(`Груп: Python ${expected.length}, сайт ${actual.length}, розбіжностей: ${differ}`);
process.exit(differ ? 1 : 0);
