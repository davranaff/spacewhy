// ----------------------------------------------------------------------

export default function Loading() {
  return (
    <div
      role="progressbar"
      aria-label="Loading page"
      aria-valuetext="Loading"
      className="spacewhy-route-loader"
    >
      <span />
      <style>{`
        .spacewhy-route-loader {
          position: fixed;
          z-index: 14000;
          inset: 0 0 auto;
          height: 3px;
          overflow: hidden;
          pointer-events: none;
          background: rgba(127, 127, 140, 0.16);
        }

        .spacewhy-route-loader > span {
          display: block;
          width: 42%;
          height: 100%;
          border-radius: 999px;
          background: #7c6cff;
          transform: translateX(-120%);
          animation: spacewhy-route-progress 760ms cubic-bezier(0.4, 0, 0.2, 1) infinite;
        }

        @keyframes spacewhy-route-progress {
          to { transform: translateX(340%); }
        }

        @media (prefers-reduced-motion: reduce) {
          .spacewhy-route-loader > span {
            width: 100%;
            transform: none;
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}
