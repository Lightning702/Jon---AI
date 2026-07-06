interface Props {
    disabled: boolean;
    onSend: (text: string) => void;
    onStop: () => void;
    streaming: boolean;
}
export default function Composer({ disabled, onSend, onStop, streaming }: Props): import("react").JSX.Element;
export {};
