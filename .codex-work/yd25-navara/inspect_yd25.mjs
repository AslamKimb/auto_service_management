import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/user/Downloads/YD25- NAVARA.xlsx";
const outputPath = "C:/Users/user/Documents/Coded/DMS/.codex-work/yd25-navara/source_inspect.json";

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheetSummary = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 10000,
  tableMaxRows: 8,
  tableMaxCols: 20,
  tableMaxCellChars: 120,
});

const sheets = [];
for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange();
  const values = used?.values ?? [];
  sheets.push({
    name: sheet.name,
    rowCount: values.length,
    columnCount: values.reduce((max, row) => Math.max(max, row.length), 0),
    sample: values.slice(0, 12),
    values,
  });
}

await fs.writeFile(
  outputPath,
  JSON.stringify({ inspect: sheetSummary.ndjson, sheets }, null, 2),
  "utf8",
);
console.log(JSON.stringify({ outputPath, sheets }, null, 2));
