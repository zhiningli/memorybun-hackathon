// Plot Grid Component - Reusable grid with axes for plotting

export const PlotGrid = (): JSX.Element => {
  return (
    <div className="flex flex-col relative z-10 pointer-events-none -mt-16">
      {/* Plot Grid Label */}
      <h2 className="text-base sm:text-base 2xl:text-xl font-normal text-black mb-2 pointer-events-none">
        Plot Grid
      </h2>

      {/* Canvas with Grid Background - scales with viewport, smaller on small screens */}
      <div className="relative w-[clamp(150px,25vw,450px)] h-[clamp(150px,25vw,450px)]">
        {/* Background grid with axes */}
        <div className="absolute inset-0 w-full h-full border-2 border-[#1D5FE4]/60 shadow-lg"
          style={{
            backgroundImage: `radial-gradient(circle, #000 1px, transparent 1px)`,
            backgroundSize: '20px 20px'
          }}
        >
          {/* Y-axis (full vertical line through center) */}
          <div 
            className="absolute left-1/2 top-[10%] -translate-x-1/2 w-0.5 bg-black pointer-events-none"
            style={{ height: '80%' }}
          >
            {/* Arrow at top (+y) */}
            <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-b-8 border-l-transparent border-r-transparent border-b-black"></div>
          </div>

          {/* X-axis (full horizontal line through center) */}
          <div 
            className="absolute left-[10%] top-1/2 -translate-y-1/2 h-0.5 bg-black pointer-events-none"
            style={{ width: '80%' }}
          >
            {/* Arrow at right (+x) */}
            <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-l-8 border-t-transparent border-b-transparent border-l-black"></div>
          </div>

          {/* Center point */}
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 bg-black rounded-full pointer-events-none z-10"></div>
        </div>
      </div>
    </div>
  );
};

