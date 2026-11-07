import type {PresenterId} from '../game/presenters';
import type {ModeId} from '../game/modes';
import type {Rect,Scene} from '../game/types';
export const EXTRA_GAMES=['maze','whack','vending','memory','lager'] as const;
export type ExtraGameId=typeof EXTRA_GAMES[number];
export type Direction='up'|'down'|'left'|'right';
export interface CompatibilityContext {randomized:boolean;guardMarker:number;cursorCue:number;selectionSeed:number;variantCue:number}
export type ExtraAction=
 |{type:'lager-route';page:string;focus:number}|{type:'focus';controlId:number}|{type:'page';page:string}|{type:'main-menu'|'archive-quit'|'dispatch-code'|'stop'}
 |{type:'instructions';subtitles:boolean}|{type:'digit';digit:number}
 |{type:'game';action:string}|({type:'maze-route'}&MazeRoute)|{type:'whack-hit';correct:boolean;positionSeed:number}|{type:'whack-next'|'whack-menu'}|{type:'vending-table'|'vending-order'}|{type:'vending-digit';digit:number;correct:boolean;nextStage:number|null}|{type:'memory-first'|'memory-next'}|{type:'memory-choice';objectId:number}|{type:'memory-stage';stage:number};
export interface ExtraVariant {startTicks:number;endTicks:number;rect:Rect;highlightSrc:string;action:ExtraAction}
export interface ExtraControl {id:number;label:string;neighbours:Record<Direction,number>;autoActivate:boolean;variants:ExtraVariant[]}
export interface ExtraPage {id:string;scene:string;loop:boolean;focus:number;controls:ExtraControl[];after:ExtraAction|null}
export interface ExtraMainControl {label:string;rect:Rect;highlightSrc:string;windows:{startTicks:number;endTicks:number;selectionSeed:number}[]}
export interface ExtraGameDefinition {menuPage:string;instructionPage:string}
export interface MazeRoute {page:string;focus:number}
export interface MazeData {entry:MazeRoute;nodes:Record<string,{lives:number;docking:number;victory:boolean}>}
export interface VariantCueWindow {startTicks:number;endTicks:number;variantCue:number}
export interface QuizEntryData {mainOne:ExtraMainControl['windows'];holly:Record<PresenterId,VariantCueWindow[]>;secondMode:Record<ModeId,VariantCueWindow[]>;setups:Record<string,Record<PresenterId|'two',string[]>>}
export interface WhackData {positions:string[];results:string[];cursorCycle:number[]}
export interface WhackState {attempt:number;score:number;appearance:number;cursorStep:number;positionSeed:number}
export interface VendingProduct {id:string;pages:string[]}
export interface VendingRound {intro:[string,string];products:VendingProduct[];randomRange:number;cueProducts:Record<string,string>;defaultProduct:string;successPage:string;wrongPage:string}
export interface VendingData {rounds:VendingRound[];initialCues:Record<string,number>;initialCueDefault:number;initialRandomRange:number;roundCueOverrides:[Record<string,number>,Record<string,number>];completePage:string}
export interface VendingState {round:number;order:number;productId:string|null;entered:number[];correctDigits:number;successes:number;usedProducts:string[];productCue:number}
export interface MemoryRound {length:number;intro:string;recall:string[];recallFocus:(number|null)[];results:string[];alwaysCorrectLast:boolean}
export interface MemoryData {objects:{id:number;label:string;page:string}[];rounds:MemoryRound[];legacyOffsets:Record<string,number>;initialLegacyCues:[number,number];initialVariantThreshold:number}
export interface MemoryState {stage:number;phase:'menu'|'intro'|'show'|'recall'|'result';cue:number;shown:number[];recalled:number[];score:number;cursor:number}
export interface LagerData {entry:string;stages:string[];nodes:Record<string,{stage:number;phase:'intro'|'aim'|'hit'|'transition'|'interlude'|'fail'}>}
export interface ExtrasData {
 lager?:LagerData;
 memory?:MemoryData;
 vending?:VendingData;
 whack?:WhackData;
 quizEntry?:QuizEntryData;
 maze?:MazeData;
 schemaVersion:1;sourceFingerprint:string;scenes:Scene[];pages:ExtraPage[];
 main:{instructions:ExtraMainControl;archive:ExtraMainControl};
 subtitles:{scene:string;src:string;startTicks:number;endTicks:number}[];
 codes:Record<string,ExtraGameId>;games:Record<ExtraGameId,ExtraGameDefinition>;
}
export interface ExtrasState {lager:LagerData['nodes'][string]|null;memory:MemoryState|null;vending:VendingState|null;stopped:boolean;whack:WhackState|null;maze:{lives:number;docking:number}|null;pageId:string;sceneToken:number;ready:boolean;focus:number;code:string;subtitles:boolean;gameId:ExtraGameId|null;context:CompatibilityContext;exit:'main-menu'|'restart'|null}
export type ExtraEvent={type:'SCENE_READY';token:number}|{type:'SCENE_WAITING';token:number}|{type:'SCENE_ENDED';token:number}
 |{type:'ACTIVATE'|'FOCUS';token:number;controlId:number;time:number}
 |{type:'MOVE';token:number;direction:Direction;time:number};
