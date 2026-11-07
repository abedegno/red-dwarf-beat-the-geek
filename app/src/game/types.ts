export type ChoiceId = 'A' | 'B' | 'C' | 'D';
export interface Rect { x: number; y: number; width: number; height: number }
export interface Choice { id: ChoiceId; label: string; rect: Rect; highlightSrc: string }
export interface Scene { id: string; src: string; durationSeconds: number; kind: 'clip' | 'question-loop' | 'still'; audioVariant: number | null }
export interface AnswerWindow { feedbackVariant?:string; startTicks: number; endTicks: number; choiceId: ChoiceId; nextCandidateMask: number }
export interface Question {
  id: string; text: string; kind: 'single' | 'sequence'; choices: Choice[];
  correctChoice: ChoiceId | null; correctSequence: ChoiceId[];
  promptScene: string; revealScene: string | null;
  durationSeconds: number; revealSeconds: number; windows: AnswerWindow[];
}
export interface SelectionState { usedMask: number; candidateMask: number; variant: number }
export interface SelectionOption { questionId: string; introScenes: string[]; variant: number }
export interface SelectionResult { questionId: string; introScenes: string[]; state: SelectionState }
export type SelectionTable = Record<string, SelectionOption[]>;
export interface Control { label: string; rect: Rect; highlightSrc: string }
export interface Ending { scenes: string[]; loopScene: string | null; continue?: Control }
export interface FeedbackTable { answers: Record<string, string[]>; endings: Record<string, Ending> }
export interface Menu extends Control { id: string; scene: string; windows: { startTicks: number; endTicks: number; candidateMask: number }[] }
export interface EntryFlow { boot: string[]; menus: Menu[]; setupScenes: string[]; roundIntros: Record<string, string[]> }
export interface RoundData { schemaVersion: 1; sourceFingerprint: string; scenes: Scene[]; questions: Question[]; selection: SelectionTable; feedback: FeedbackTable; entry: EntryFlow }
export type Phase = 'idle' | 'boot' | 'menu' | 'entry' | 'question-intro' | 'question' | 'feedback' | 'ending' | 'complete';
export type QueueDestination = 'menu' | 'question' | 'next-question' | 'complete';
export interface RoundState {
  phase: Phase; activeScene: string | null; sceneToken: number; ready: boolean;
  queue: string[]; destination: QueueDestination; menuIndex: number;
  questionNumber: number; score: number; questionId: string | null;
  selection: SelectionState; chosenAnswers: ChoiceId[]; nextCandidateMask: number;
  endingKey: string | null;
}
export type RoundEvent =
  | { type: 'START' } | { type: 'RESET' }
  | { type: 'SCENE_READY' | 'SCENE_WAITING' | 'SCENE_ENDED' | 'CONTINUE'; token: number }
  | { type: 'MENU_CHOOSE'; token: number; time: number }
  | { type: 'ANSWER'; token: number; time: number; choiceId: ChoiceId };

// Complete supported one-player path. These are semantic records, not DVD state.
export interface ActiveInterval { startTicks:number; endTicks:number }
export interface TimedControl extends Control { windows:ActiveInterval[] }
export interface GameQuestion extends Question { expiry:'loop'|'timeout'; promptPlays?:number }
export interface TimeoutOutcome { feedback:string[]; nextCandidateMask:number }
export interface PresentationGate { scene:string; control:TimedControl; loop:boolean; afterScenes:string[] }
export interface GamePresentation {
  scenes:string[]; gate?:PresentationGate; nextOrderingRepeatOffset?:number;
  destination:'next-level'|'complete'|'bonus'; nextCandidateMask:number;
}
export interface LevelData {
  number:number; questions:GameQuestion[]; selection:SelectionTable;
  answers:Record<string,string[]>; timeouts:Record<string,TimeoutOutcome[]>;
  intros:Record<string,string[]>; endings:Record<string,GamePresentation>;
}
export interface BonusData {
  id:string; introScenes:string[]; question:GameQuestion;
  correct:GamePresentation; wrong:GamePresentation;
}
export interface GameData {
  randomized?:boolean;
  schemaVersion:2; sourceFingerprint:string; scenes:Scene[];
  entry:Omit<EntryFlow,'roundIntros'> & {setupOptions?:string[][]}; levels:LevelData[]; bonuses:BonusData[];
}
export type GamePhase=Phase|'bonus-intro'|'bonus'|'bonus-feedback';
export type GameDestination='menu'|'question'|'next-question'|'next-level'|'complete'|'bonus'|'bonus-question';
export interface GameState {
  phase:GamePhase; activeScene:string|null; sceneToken:number; ready:boolean;
  queue:string[]; destination:GameDestination; menuIndex:number; levelIndex:number;
  orderingRepeatOffset:number; promptCompleted:number; questionNumber:number; roundScore:number; totalScore:number; questionId:string|null;
  selection:SelectionState; chosenAnswers:ChoiceId[]; nextCandidateMask:number;
  currentPresentation:GamePresentation|null; timeoutOutcome:TimeoutOutcome|null; bonusId:string|null;
}
export type GameEvent=Exclude<RoundEvent,{type:'SCENE_READY'|'SCENE_WAITING'|'SCENE_ENDED'|'CONTINUE'}>
  | {type:'SCENE_READY'|'SCENE_WAITING'|'SCENE_ENDED';token:number}
  | {type:'CONTINUE';token:number;time:number};
