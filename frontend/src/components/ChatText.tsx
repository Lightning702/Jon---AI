import { isValidElement, memo, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ohneTabellen } from "../lib/text";
import CodeBlock, { TestVorschau } from "./CodeBlock";
import "./chat-text.css";

function mitZeilenumbruechen(text: string): string {
  const teile = text.split("```");
  for (let i = 0; i < teile.length; i += 2) {
    teile[i] = teile[i].replace(/([^\n])\n(?!\n|\s*[-*+]\s|\s*\d+[.)]\s|\s*#|\s*>|\s*---)/g, "$1  \n");
  }
  if (teile.length % 2 === 0) teile.push("");
  return teile.join("```");
}

function codeAus(kinder: ReactNode): { sprache: string; code: string } {
  const kind = Array.isArray(kinder) ? kinder[0] : kinder;
  if (!isValidElement(kind)) return { sprache: "", code: String(kinder ?? "") };
  const eigenschaften = kind.props as { className?: string; children?: ReactNode };
  const sprache = /language-([\w+#-]+)/.exec(eigenschaften.className || "")?.[1] ?? "";
  const inhalt = Array.isArray(eigenschaften.children) ? eigenschaften.children.join("") : String(eigenschaften.children ?? "");
  return { sprache, code: inhalt.replace(/\n$/, "") };
}

function ChatText({ text, fertig = true }: { text: string; fertig?: boolean }) {
  return (
    <div className="chat-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) =>
            href && /^(?:https?:\/\/[^/]+)?\/testumgebung-vorschau\//.test(href) ? (
              <TestVorschau pfad={href.replace(/^https?:\/\/[^/]+/, "")} titel={typeof children === "string" ? children : undefined} />
            ) : (
              <a href={href} target="_blank" rel="noreferrer noopener">
                {children}
              </a>
            ),
          pre: ({ children }) => {
            const { sprache, code } = codeAus(children);
            return <CodeBlock sprache={sprache} code={code} fertig={fertig} />;
          },
        }}
      >
        {mitZeilenumbruechen(ohneTabellen(text))}
      </ReactMarkdown>
    </div>
  );
}

export default memo(ChatText);
