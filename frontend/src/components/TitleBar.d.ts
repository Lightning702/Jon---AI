declare global {
    interface Window {
        jon?: {
            minimize: () => void;
            maximize: () => void;
            close: () => void;
            platform: string;
        };
    }
}
export default function TitleBar(): import("react").JSX.Element;
