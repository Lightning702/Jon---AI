import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ohneTabellen } from "../lib/text";
import "./chat-text.css";

function mitZeilenumbruechen(text: string): string {
  const teile = text.split("```");
  for (let i = 0; i < teile.length; i += 2) {
    teile[i] = teile[i].replace(/([^\n])\n(?!\n|\s*[-*+]\s|\s*\d+[.)]\s|\s*#|\s*>|\s*---)/g, "$1  \n");
  }
  if (teile.length % 2 === 0) teile.push("");
  return teile.join("```");
}

function ChatText({ text }: { text: string }) {
  return (
    <div className="chat-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          ),
        }}
      >
        {mitZeilenumbruechen(ohneTabellen(text))}
      </ReactMarkdown>
    </div>
  );
}

export default memo(ChatText);
