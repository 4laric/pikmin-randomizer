        if(ticks%5==0){
            float maxDepth=-100000,high=0;DynParticle* hit=nullptr;
            for(auto* part=cargo->mParticleList;part;part=part->mNextParticle){
                float h=mapMgr->getMinY(part->mWorldPosition.x,part->mWorldPosition.z,true);
                float depth=h-part->mWorldPosition.y+part->mCollisionRadius;
                if(depth>maxDepth){maxDepth=depth;hit=part;high=h;}
            }
            if(hit){auto pos=hit->mWorldPosition;
                std::printf("P2_DONUT_PARTICLE p=%.3f,%.3f,%.3f highest=%.3f depth=%.3f pick=%.3f\n",pos.x,pos.y,pos.z,high,maxDepth,cargo->getPickOffset());}
            auto pos=cargo->mSRT.t;auto v=cargo->mVelocity;auto carry=cargo->mCarryDirection;
            auto norm=cargo->mGroundTriangle?cargo->mGroundTriangle->mTriangle.mNormal:Vector3f(0,0,0);
            std::printf("P2_DONUT_MOTION p=%.4f,%.4f,%.4f v=%.4f,%.4f,%.4f carry=%.4f,%.4f,%.4f normal=%.4f,%.4f,%.4f ground=%d collision=%u changed=%u navi=%.3f,%.3f,%.3f\n",pos.x,pos.y,pos.z,v.x,v.y,v.z,carry.x,carry.y,carry.z,norm.x,norm.y,norm.z,int(cargo->onGround()),cargo->mCollisionOccurred,cargo->mHasCollChangedVelocity,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z);
        }
