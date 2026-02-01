import { useState } from "react";
import { Avatar, AvatarFallback } from "../../components/ui/avatar";
import { Button } from "../../components/ui/button";
import { QuestionListSection, WelcomeBackSection } from "./sections";

const navigationItems = [
  { label: "Problems" },
  { label: "Store" },
  { label: "Feedback" },
];

export const QuestionMenu = (): JSX.Element => {
  const [activeTab, setActiveTab] = useState(0);

  const handleTabClick = (index: number) => {
    setActiveTab(index);
  };

  return (
    <div className="bg-white w-full min-h-screen flex flex-col">
      <header className="w-full h-[60px] 2xl:h-[70px] flex items-center justify-between px-4 sm:px-6 md:px-8 border-b border-gray-200">
        <div className="flex items-center gap-2 md:gap-4 flex-shrink-0">
          <Button variant="ghost" size="icon" className="w-20 md:w-[132px] h-12 p-0">
          <img
            className="w-20 md:w-[132px] h-auto"
            alt="Memorybun"
            src="/MemoryBun_logo_3.png"
          />
          </Button>
        </div>

        <nav className="flex items-center gap-6 sm:gap-8 md:gap-10 lg:gap-12 flex-1 justify-center">
          {navigationItems.map((item, index) => {
            const isActive = activeTab === index;
            return (
              <button
                key={index}
                onClick={() => handleTabClick(index)}
                className={`relative text-sm sm:text-base md:text-lg font-medium ${
                  isActive ? "text-[#0052f9] font-semibold" : "text-[#0052f9b2]"
                } transition-colors duration-200 cursor-pointer hover:text-[#0052f9] pb-1`}
              >
                {item.label}
                {isActive && (
                  <div className="absolute -bottom-[14px] 2xl:-bottom-[18px] left-0 right-0 h-0.5 bg-[#0052f9]" />
                )}
              </button>
            );
          })}
        </nav>

        <Avatar className="w-10 h-10 sm:w-12 sm:h-12 flex-shrink-0">
          <AvatarFallback className="bg-gradient-to-br from-blue-400 to-purple-500 text-white font-semibold">P</AvatarFallback>
        </Avatar>
      </header>

      <main className="flex-1 w-full px-4 sm:px-8 md:px-16 lg:px-28 xl:px-32 2xl:px-24 pt-8 md:pt-12 max-w-[1600px] mx-auto">
        <WelcomeBackSection />
        <QuestionListSection />
      </main>
    </div>
  );
};
