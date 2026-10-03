import React from 'react';

interface ControlledMarkdownProps {
  content: string;
  className?: string;
}

/**
 * Controlled, secure markdown renderer supporting:
 * - Markdown tables (| Header 1 | Header 2 |)
 * - Code blocks (```code```) and inline code (`code`)
 * - Bullet lists (- or * item)
 * - Bold (**bold**) and Italic (*italic*)
 * - Escaping and sanitizing untrusted input
 */
export const ControlledMarkdown: React.FC<ControlledMarkdownProps> = ({ content, className = '' }) => {
  if (!content) return null;

  // Split into structural blocks (tables, code blocks, paragraphs)
  const lines = content.split('\n');
  const blocks: React.ReactNode[] = [];
  let tableBuffer: string[] = [];
  let codeBuffer: string[] = [];
  let inCodeBlock = false;

  const flushTable = () => {
    if (tableBuffer.length < 2) {
      tableBuffer.forEach((l, idx) => blocks.push(<p key={`tbl-fallback-${blocks.length}-${idx}`}>{renderInline(l)}</p>));
      tableBuffer = [];
      return;
    }

    const parseRow = (row: string) =>
      row
        .trim()
        .replace(/^\|/, '')
        .replace(/\|$/, '')
        .split('|')
        .map((cell) => cell.trim());

    const headerCells = parseRow(tableBuffer[0]);
    // Row 1 is divider (|---|---|)
    const bodyRows = tableBuffer.slice(2).map(parseRow);

    blocks.push(
      <div key={`table-${blocks.length}`} className="my-3 overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-muted/80 text-foreground font-semibold border-b border-border">
            <tr>
              {headerCells.map((h, i) => (
                <th key={i} className="px-3 py-2">
                  {renderInline(h)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {bodyRows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-muted/30 transition-colors">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                    {renderInline(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    tableBuffer = [];
  };

  const flushCode = () => {
    if (codeBuffer.length > 0) {
      blocks.push(
        <pre
          key={`code-${blocks.length}`}
          className="my-3 p-3 bg-muted/90 rounded-lg text-xs font-mono overflow-x-auto border border-border/70 text-foreground"
        >
          <code>{codeBuffer.join('\n')}</code>
        </pre>
      );
      codeBuffer = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Check code blocks
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        inCodeBlock = false;
        flushCode();
      } else {
        if (tableBuffer.length > 0) flushTable();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      continue;
    }

    // Check table row (| ... |)
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      tableBuffer.push(line.trim());
      continue;
    } else if (tableBuffer.length > 0) {
      flushTable();
    }

    // Bullet points
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      blocks.push(
        <li key={`li-${i}`} className="ml-4 list-disc text-sm text-foreground my-0.5 leading-relaxed">
          {renderInline(line.trim().substring(2))}
        </li>
      );
      continue;
    }

    // Regular line / paragraph
    if (line.trim().length > 0) {
      blocks.push(
        <p key={`p-${i}`} className="text-sm text-foreground my-1.5 leading-relaxed">
          {renderInline(line)}
        </p>
      );
    }
  }

  if (tableBuffer.length > 0) flushTable();
  if (codeBuffer.length > 0) flushCode();

  return <div className={`space-y-1 ${className}`}>{blocks}</div>;
};

/**
 * Renders inline elements: bold, italic, inline code
 */
function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  // Tokenize regex for **bold** and `code`
  const regex = /(\*\*.*?\*\*|`.*?`)/g;
  let lastIdx = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push(text.substring(lastIdx, match.index));
    }
    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={match.index} className="font-semibold text-foreground">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code key={match.index} className="px-1.5 py-0.5 rounded bg-muted font-mono text-xs text-primary">
          {token.slice(1, -1)}
        </code>
      );
    }
    lastIdx = regex.lastIndex;
  }

  if (lastIdx < text.length) {
    parts.push(text.substring(lastIdx));
  }

  return parts.length > 0 ? parts : text;
}
